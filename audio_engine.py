import math
import shutil
import subprocess
import tempfile
from pathlib import Path
import numpy as np

MAX_BYTES = 150 * 1024 * 1024
FORMATS = {
    'wav': ('wav', 'audio/wav', ['-c:a', 'pcm_s24le']),
    'wav32': ('wav', 'audio/wav', ['-c:a', 'pcm_f32le']),
    'flac': ('flac', 'audio/flac', ['-c:a', 'flac', '-sample_fmt', 's32', '-compression_level', '12']),
    'mp3': ('mp3', 'audio/mpeg', ['-c:a', 'libmp3lame', '-b:a', '320k', '-compression_level', '0']),
}
PROFILES = {
    'auto': 'Otomatik öneri',
    'focus': 'Vokal / merkez odak',
    'wide': 'Enstrümantal / geniş stereo',
}


def select_profile(samples, requested):
    """Stereo geometry is measurable; genre and perceived quality are not inferred."""
    if requested != 'auto':
        return requested, 'Elle seçilen profil uygulandı.'
    if not len(samples) or np.max(np.abs(samples)) < 1e-6:
        return 'focus', 'Sessiz veya çok düşük seviyeli kayıt: merkez odak önerildi.'
    mid = (samples[:, 0] + samples[:, 1]) * 0.5
    side = (samples[:, 0] - samples[:, 1]) * 0.5
    mid_energy = float(np.mean(mid.astype(np.float64) ** 2))
    side_energy = float(np.mean(side.astype(np.float64) ** 2))
    ratio = mid_energy / max(mid_energy + side_energy, 1e-20)
    if ratio >= 0.65:
        return 'focus', f'Merkez enerji payı %{ratio * 100:.0f}: vokal / merkez odak önerildi.'
    return 'wide', f'Merkez enerji payı %{ratio * 100:.0f}: geniş stereo önerildi.'


def analyse_profile(ffmpeg, source, folder, requested):
    if requested != 'auto':
        return select_profile(np.empty((0, 2)), requested)
    analysis = Path(folder) / 'analysis.f32'
    # Analyse the whole recording with bounded-memory, low-rate stereo measurements.
    run_audio([ffmpeg, '-v', 'error', '-nostdin', '-y', '-i', str(source), '-map', '0:a:0', '-ac', '2', '-ar', '12000', '-f', 'f32le', str(analysis)])
    if not analysis.stat().st_size:
        raise AudioError('Ses kaydı boş.')
    samples = np.memmap(analysis, dtype='<f4', mode='r').reshape(-1, 2)
    try:
        # Up to 120k evenly distributed frames keeps RAM and analysis work bounded.
        measured = np.array(samples[::max(1, len(samples) // 120000)])
        if not np.isfinite(measured).all():
            raise AudioError('Ses kaydı geçersiz örnekler içeriyor.')
        return select_profile(measured, requested)
    finally:
        del samples


def profile_options(profile):
    return ['--centre-focus'] if profile == 'focus' else []


def rubberband_path():
    bundled = Path(__file__).parent / 'tools' / 'rubberband' / 'rubberband-4.0.0-gpl-executable-windows' / 'rubberband.exe'
    return str(bundled) if bundled.is_file() else shutil.which('rubberband')


def run_audio(command):
    try:
        result = subprocess.run(command, capture_output=True, timeout=1200)
    except subprocess.TimeoutExpired:
        raise AudioError('İşlem zaman aşımına uğradı. Daha kısa bir dosya deneyin.')
    if result.returncode:
        raise AudioError('Ses işlenemedi. Geçerli bir MP3/WAV dosyası ve Rubber Band 3+ kurulumu gerekiyor.')


class AudioError(ValueError):
    pass


def convert(stream, filename, speed, output_format, profile='auto', metadata=None):
    try:
        speed = float(speed)
    except (ValueError, TypeError):
        raise AudioError('Geçerli bir hız seçin.')
    if not math.isfinite(speed) or not 0.5 <= speed <= 2:
        raise AudioError('Hız 0.50 ile 2.00 arasında olmalı.')
    if output_format not in FORMATS:
        raise AudioError('Geçerli bir çıktı formatı seçin.')
    if profile not in PROFILES:
        raise AudioError('Geçerli bir işleme profili seçin.')
    extension = Path(filename or '').suffix.lower()
    if extension not in {'.wav', '.mp3'}:
        raise AudioError('Lütfen MP3 veya WAV yükleyin.')
    ffmpeg = shutil.which('ffmpeg')
    if not ffmpeg:
        raise AudioError('FFmpeg bulunamadı.')
    rubberband = rubberband_path()
    if speed != 1 and not rubberband:
        raise AudioError('Yüksek kaliteli Rubber Band R3 motoru bulunamadı. Kurulum yönergelerine bakın.')
    suffix, _, codec = FORMATS[output_format]
    with tempfile.TemporaryDirectory(prefix='tempo-') as folder:
        source = Path(folder) / ('input' + extension)
        target = Path(folder) / ('output.' + suffix)
        total = 0
        with source.open('wb') as destination:
            while chunk := stream.read(1024 * 1024):
                total += len(chunk)
                if total > MAX_BYTES:
                    raise AudioError('Dosya en fazla 150 MB olabilir.')
                destination.write(chunk)
        if total == 0:
            raise AudioError('Dosya boş.')
        chosen, reason = analyse_profile(ffmpeg, source, folder, profile)
        if metadata is not None:
            metadata.update(profile=chosen, profile_label=PROFILES[chosen], reason=reason, speed=speed)
        prefix = [ffmpeg, '-hide_banner', '-loglevel', 'error', '-nostdin', '-y']
        processed = source
        if speed != 1:
            decoded = Path(folder) / 'decoded.wav'
            processed = Path(folder) / 'stretched.wav'
            # Float intermediates avoid integer quantisation before the final export.
            # Do not resample or split stereo channels. Offline R3 studies the whole file.
            run_audio(prefix + ['-i', str(source), '-map', '0:a:0', '-vn', '-c:a', 'pcm_f32le', str(decoded)])
            run_audio([rubberband, '--fine', '--tempo', str(speed), '--frequency', '1', *profile_options(chosen), '--quiet', str(decoded), str(processed)])
        # 1x skips time stretching. No EQ, denoising, or loudness normalisation.
        export = prefix + ['-i', str(processed), '-map', '0:a:0', '-vn']
        if output_format in {'wav', 'flac'}:
            export += ['-af', 'aresample=dither_method=triangular']
        run_audio(export + codec + [str(target)])
        return target.read_bytes()


def listening_copy(stream, filename):
    """Decode an already rendered export for browsers, without time stretching again."""
    extension = Path(filename or '').suffix.lower()
    if extension not in {'.wav', '.mp3', '.flac'}:
        raise AudioError('Önizleme için WAV, FLAC veya MP3 gerekiyor.')
    ffmpeg = shutil.which('ffmpeg')
    if not ffmpeg:
        raise AudioError('FFmpeg bulunamadı.')
    with tempfile.TemporaryDirectory(prefix='tempo-listen-') as folder:
        source = Path(folder) / ('input' + extension)
        target = Path(folder) / 'listen.wav'
        total = 0
        with source.open('wb') as destination:
            while chunk := stream.read(1024 * 1024):
                total += len(chunk)
                # Rendered files can be larger than their compressed source.
                if total > 1024 * 1024 * 1024:
                    raise AudioError('Dinleme kopyası en fazla 1 GB olabilir.')
                destination.write(chunk)
        run_audio([ffmpeg, '-v', 'error', '-nostdin', '-y', '-i', str(source), '-map', '0:a:0', '-vn', '-c:a', 'pcm_s24le', str(target)])
        return target.read_bytes()
