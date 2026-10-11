from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from audio_engine import AudioError, convert, FORMATS, listening_copy

app = FastAPI(title='Tempo Studio')
app.mount('/static', StaticFiles(directory=Path(__file__).parent / 'static'), name='static')


@app.get('/')
def index():
    return FileResponse(Path(__file__).parent / 'static' / 'index.html')


@app.post('/api/process')
def process(file: UploadFile = File(...), speed: str = Form('1'), output_format: str = Form('wav'), profile: str = Form('auto')):
    metadata = {}
    try:
        data = convert(file.file, file.filename, speed, output_format, profile, metadata)
    except AudioError as error:
        raise HTTPException(400, str(error))
    suffix, mime, _ = FORMATS[output_format]
    return Response(data, media_type=mime, headers={'Content-Disposition': f'attachment; filename="tempo-{float(speed):.2f}x.{suffix}"', 'X-Tempo-Profile': metadata['profile'], 'X-Tempo-Reason': quote(metadata['reason'])})


@app.post('/api/listen')
def listen(file: UploadFile = File(...)):
    try:
        data = listening_copy(file.file, file.filename)
    except AudioError as error:
        raise HTTPException(400, str(error))
    return Response(data, media_type='audio/wav')
