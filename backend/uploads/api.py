from fastapi import APIRouter, UploadFile, File, HTTPException
from utils import invoke_uid, image_extensions, video_extensions

upload_router = APIRouter(tags=['uploads'])


@upload_router.post("/file/{client_address:str}/upload")
async def upload_file(client_address: str, file: UploadFile = File(...)):
    fid = invoke_uid()
    print(file.filename)
    file_name = file.filename
    if file_name.split('.')[-1].lower() in image_extensions:
        file_name = f'{client_address}_{fid}.jpg'
    elif file_name.split('.')[-1].lower() in video_extensions:
        file_name = f'{client_address}_{fid}.mp4'
    else:
        raise HTTPException(401, '')
    with open(f'assets/{file_name}', "wb") as f:
        f.write(await file.read())
    return {'id': file_name}
