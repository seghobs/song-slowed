import io
import unittest
import wave
import subprocess
import numpy as np
from fastapi.testclient import TestClient
from app import app
from flask_app import app as flask_app
from audio_engine import convert, rubberband_path, select_profile, profile_options, listening_copy


def tone():
    t = np.arange(44100 * 3) / 44100
    samples = (np.sin(2 * np.pi * 440 * t) * 16000).astype('<i2')
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(44100)
        wav.writeframes(samples.tobytes())
    return buffer.getvalue()


class AudioTests(unittest.TestCase):
    def test_profile_measurements(self):
        t = np.arange(12000) / 12000
        centre = np.sin(2 * np.pi * 440 * t)
        other = np.sin(2 * np.pi * 660 * t)
        self.assertEqual(select_profile(np.column_stack((centre, centre)), 'auto')[0], 'focus')
        self.assertEqual(select_profile(np.column_stack((centre, other)), 'auto')[0], 'wide')
        self.assertEqual(select_profile(np.zeros((100, 2)), 'auto')[0], 'focus')
        self.assertEqual(select_profile(np.column_stack((centre, centre)), 'wide')[0], 'wide')
        self.assertEqual(profile_options('focus'), ['--centre-focus'])
        self.assertEqual(profile_options('wide'), [])

    def test_profile_apis_and_listening_copy(self):
        client = TestClient(app)
        for profile in ('auto', 'focus', 'wide'):
            response = client.post('/api/process', files={'file': ('tone.wav', tone())}, data={'profile': profile, 'speed': '0.8', 'output_format': 'flac'})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers['X-Tempo-Profile'], 'wide' if profile == 'wide' else 'focus')
            preview = client.post('/api/listen', files={'file': ('output.flac', response.content)})
            self.assertEqual(preview.status_code, 200)
            with wave.open(io.BytesIO(preview.content)) as wav:
                self.assertEqual(wav.getframerate(), 44100)
                self.assertAlmostEqual(wav.getnframes() / wav.getframerate(), 3 / 0.8, delta=0.1)
        bad = client.post('/api/process', files={'file': ('tone.wav', tone())}, data={'profile': 'unknown'})
        self.assertEqual(bad.status_code, 400)
        with flask_app.test_client() as flask:
            response = flask.post('/api/process', data={'file': (io.BytesIO(tone()), 'tone.wav'), 'profile': 'wide', 'speed': '0.8'})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers['X-Tempo-Profile'], 'wide')
            self.assertEqual(flask.post('/api/listen', data={'file': (io.BytesIO(response.data), 'render.wav')}).status_code, 200)

    def test_r3_installed(self):
        result = subprocess.run([rubberband_path(), '--version'], capture_output=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn(b'4.0.0', result.stdout + result.stderr)

    def test_stereo_exports_and_mp3_input(self):
        rate = 48000
        t = np.arange(rate * 2) / rate
        # Different notes verify channel separation, plus a common centre component.
        left = 0.2 * np.sin(2 * np.pi * 440 * t) + 0.08 * np.sin(2 * np.pi * 220 * t)
        right = 0.2 * np.sin(2 * np.pi * 660 * t) + 0.08 * np.sin(2 * np.pi * 220 * t)
        stereo = np.column_stack((left, right))
        source = io.BytesIO()
        with wave.open(source, 'wb') as wav:
            wav.setnchannels(2)
            wav.setsampwidth(2)
            wav.setframerate(rate)
            wav.writeframes((stereo * 32767).astype('<i2').tobytes())
        for output_format in ('wav', 'wav32', 'flac', 'mp3'):
            data = convert(io.BytesIO(source.getvalue()), 'stereo.wav', 0.8, output_format)
            result = subprocess.run(['ffmpeg', '-v', 'error', '-i', 'pipe:0', '-f', 'f32le', '-acodec', 'pcm_f32le', 'pipe:1'], input=data, capture_output=True)
            self.assertEqual(result.returncode, 0)
            samples = np.frombuffer(result.stdout, dtype='<f4').reshape(-1, 2)
            self.assertTrue(np.isfinite(samples).all())
            self.assertLessEqual(np.max(np.abs(samples)), 1)
            self.assertAlmostEqual(len(samples) / rate, 2 / 0.8, delta=0.1)
            for channel, expected in ((0, 440), (1, 660)):
                segment = samples[rate // 4:rate // 4 + rate, channel]
                spectrum = abs(np.fft.rfft(segment * np.hanning(len(segment))))
                frequency = np.fft.rfftfreq(len(segment), 1 / rate)[spectrum.argmax()]
                self.assertAlmostEqual(frequency, expected, delta=2)
            if output_format == 'mp3':
                converted = convert(io.BytesIO(data), 'encoded.mp3', 1.25, 'wav')
                with wave.open(io.BytesIO(converted)) as wav:
                    self.assertEqual(wav.getnchannels(), 2)
                    self.assertEqual(wav.getframerate(), rate)
                    self.assertAlmostEqual(wav.getnframes() / rate, 2, delta=0.1)

    def test_unity_bypasses_stretch(self):
        original = tone()
        output = convert(io.BytesIO(original), 'tone.wav', 1, 'wav32')
        result = subprocess.run(['ffmpeg', '-v', 'error', '-i', 'pipe:0', '-f', 'f32le', 'pipe:1'], input=output, capture_output=True)
        with wave.open(io.BytesIO(original)) as wav:
            reference = np.frombuffer(wav.readframes(wav.getnframes()), dtype='<i2').astype(np.float32) / 32768
        np.testing.assert_array_equal(np.frombuffer(result.stdout, dtype='<f4'), reference)

    def test_duration_and_pitch(self):
        client = TestClient(app)
        for speed in (0.5, 0.75, 1, 1.25, 2):
            response = client.post('/api/process', files={'file': ('tone.wav', tone(), 'audio/wav')}, data={'speed': str(speed), 'output_format': 'wav'})
            self.assertEqual(response.status_code, 200, response.text[:100] if response.status_code != 200 else '')
            with wave.open(io.BytesIO(response.content)) as wav:
                rate = wav.getframerate()
                self.assertEqual(rate, 44100)
                self.assertAlmostEqual(wav.getnframes() / rate, 3 / speed, delta=0.12)
                data = np.frombuffer(wav.readframes(wav.getnframes()), dtype=np.uint8).reshape(-1, 3)
                samples = data[:, 0].astype(np.int32) | data[:, 1].astype(np.int32) << 8 | data[:, 2].astype(np.int32) << 16
                samples = (samples ^ 0x800000) - 0x800000
                segment = samples[rate // 4:rate // 4 + rate]
                spectrum = np.abs(np.fft.rfft(segment * np.hanning(len(segment))))
                frequency = np.fft.rfftfreq(len(segment), 1 / rate)[spectrum.argmax()]
                self.assertAlmostEqual(frequency, 440, delta=2)

    def test_invalid_input(self):
        client = TestClient(app)
        for speed in ('nan', '3', 'abc'):
            response = client.post('/api/process', files={'file': ('tone.wav', tone())}, data={'speed': speed})
            self.assertEqual(response.status_code, 400)
        response = client.post('/api/process', files={'file': ('fake.wav', b'invalid')})
        self.assertEqual(response.status_code, 400)

    def test_flask_mp3(self):
        with flask_app.test_client() as client:
            response = client.post('/api/process', data={'file': (io.BytesIO(tone()), 'tone.wav'), 'speed': '0.8', 'output_format': 'mp3'})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.mimetype, 'audio/mpeg')
            self.assertGreater(len(response.data), 1000)


if __name__ == '__main__':
    unittest.main()
