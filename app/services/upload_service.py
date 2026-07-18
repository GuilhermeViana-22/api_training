import mimetypes
from datetime import date
from io import BytesIO
from pathlib import Path

from fastapi import UploadFile
from PIL import Image
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import BusinessError
from app.repositories.attendance_repository import ProgressRepository
from app.utils.uuid import generate_uuid

progress_repo = ProgressRepository()

IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
IMAGE_MIMES = {"image/jpeg", "image/png", "image/webp"}
GIF_EXTENSIONS = {"gif"}
GIF_MIMES = {"image/gif"}
VIDEO_EXTENSIONS = {"mp4", "webm", "mov"}
VIDEO_MIMES = {"video/mp4", "video/webm", "video/quicktime"}

EXERCISE_MEDIA_TYPES = {"image", "gif", "video"}


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _validate_image(content: bytes, filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in IMAGE_EXTENSIONS:
        raise BusinessError("VALIDATION_ERROR", "Formato não suportado. Use JPEG, PNG ou WebP.", 422)

    max_bytes = settings.upload_max_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise BusinessError("VALIDATION_ERROR", f"Arquivo excede {settings.upload_max_size_mb}MB.", 422)

    try:
        image = Image.open(BytesIO(content))
        image.verify()
    except Exception as exc:
        raise BusinessError("VALIDATION_ERROR", "Arquivo de imagem inválido.", 422) from exc

    mime = mimetypes.guess_type(filename)[0]
    if mime not in IMAGE_MIMES:
        raise BusinessError("VALIDATION_ERROR", "MIME type não suportado.", 422)

    return ext


def _classify_exercise_media(content: bytes, filename: str, content_type: str) -> tuple[str, str]:
    """
    Classifica e valida uma midia de exercicio (imagem, gif ou video).

    Regras:
    - Video é decidido por MIME/extensao, sem decodificar o conteudo (arquivos grandes).
    - Imagem/gif: o tipo real é sempre confirmado pelo conteudo decodificado (Pillow),
      nunca apenas pela extensao enviada pelo cliente — um .jpg renomeado para .gif
      (ou vice-versa) é classificado pelo formato real do arquivo.
    - Retorna (extensao_normalizada, media_type) com media_type em EXERCISE_MEDIA_TYPES.
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    mime = (content_type or mimetypes.guess_type(filename)[0] or "").lower()

    if mime.startswith("video/") or ext in VIDEO_EXTENSIONS:
        ext = _validate_video(content, filename)
        return ext, "video"

    max_bytes = settings.upload_max_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise BusinessError("VALIDATION_ERROR", f"Arquivo excede {settings.upload_max_size_mb}MB.", 422)

    try:
        image = Image.open(BytesIO(content))
        image.verify()
        detected_format = (image.format or "").upper()
    except Exception as exc:
        raise BusinessError("VALIDATION_ERROR", "Arquivo de midia invalido.", 422) from exc

    if detected_format == "GIF":
        return "gif", "gif"

    if detected_format in {"JPEG", "PNG", "WEBP"}:
        return detected_format.lower().replace("jpeg", "jpg"), "image"

    raise BusinessError(
        "VALIDATION_ERROR", "Formato não suportado. Use JPEG, PNG, WebP, GIF ou video (MP4/WebM/MOV).", 422
    )


def _validate_video(content: bytes, filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in VIDEO_EXTENSIONS:
        raise BusinessError("VALIDATION_ERROR", "Formato de vídeo não suportado. Use MP4, WebM ou MOV.", 422)

    max_bytes = settings.upload_max_size_mb * 1024 * 1024 * 4  # 20MB para vídeos
    if len(content) > max_bytes:
        raise BusinessError("VALIDATION_ERROR", f"Vídeo excede {settings.upload_max_size_mb * 4}MB.", 422)

    mime = mimetypes.guess_type(filename)[0]
    if mime and mime not in VIDEO_MIMES:
        raise BusinessError("VALIDATION_ERROR", "MIME type de vídeo não suportado.", 422)

    return ext


async def save_student_photo(
    db: Session,
    student_id: str,
    file: UploadFile,
    photo_type: str = "other",
    weight_kg: float | None = None,
    notes: str | None = None,
    taken_at: date | None = None,
) -> dict:
    content = await file.read()
    ext = _validate_image(content, file.filename or "photo.jpg")

    relative_dir = Path("students") / student_id
    absolute_dir = Path(settings.upload_dir) / relative_dir
    _ensure_dir(absolute_dir)

    filename = f"{generate_uuid()}.{ext}"
    relative_path = str(relative_dir / filename)
    absolute_path = Path(settings.upload_dir) / relative_path
    absolute_path.write_bytes(content)

    photo = progress_repo.create_photo(
        db,
        student_id=student_id,
        file_path=relative_path.replace("\\", "/"),
        photo_type=photo_type,
        weight_kg=weight_kg,
        notes=notes,
        taken_at=taken_at or date.today(),
    )
    db.commit()

    return {
        "id": photo.id,
        "url": f"/api/v1/uploads/{photo.file_path}",
        "photo_type": photo.photo_type,
        "weight_kg": float(photo.weight_kg) if photo.weight_kg is not None else None,
        "taken_at": photo.taken_at.isoformat(),
        "created_at": photo.created_at.isoformat(),
    }


async def save_day_photo(
    db: Session,
    student_id: str,
    day_of_week: int,
    file: UploadFile,
    photo_type: str = "other",
    weight_kg: float | None = None,
    notes: str | None = None,
    taken_at: date | None = None,
) -> dict:
    from app.repositories.training_repository import TrainingRepository

    training_repo = TrainingRepository()
    training = training_repo.get_active_for_student(db, student_id)
    if training is None:
        raise BusinessError("TRAINING_NOT_ACTIVE", "Nenhum treino ativo para registrar foto.", 422)

    if not training_repo.day_exists(db, training.id, day_of_week):
        raise BusinessError("INVALID_DAY", "Dia de treino inválido.", 422)

    content = await file.read()
    ext = _validate_image(content, file.filename or "photo.jpg")

    relative_dir = Path("students") / student_id / "days"
    absolute_dir = Path(settings.upload_dir) / relative_dir
    _ensure_dir(absolute_dir)

    filename = f"{generate_uuid()}.{ext}"
    relative_path = str(relative_dir / filename)
    absolute_path = Path(settings.upload_dir) / relative_path
    absolute_path.write_bytes(content)

    photo = progress_repo.create_photo(
        db,
        student_id=student_id,
        file_path=relative_path.replace("\\", "/"),
        photo_type=photo_type,
        weight_kg=weight_kg,
        notes=notes,
        taken_at=taken_at or date.today(),
        training_id=training.id,
        day_of_week=day_of_week,
    )
    db.commit()

    return {
        "id": photo.id,
        "url": f"/api/v1/uploads/{photo.file_path}",
        "photo_type": photo.photo_type,
        "training_id": photo.training_id,
        "day_of_week": photo.day_of_week,
        "weight_kg": float(photo.weight_kg) if photo.weight_kg is not None else None,
        "taken_at": photo.taken_at.isoformat(),
        "created_at": photo.created_at.isoformat(),
    }


async def save_exercise_media(db: Session, exercise_id: str, file: UploadFile, sort_order: int = 0) -> dict:
    from app.repositories.exercise_repository import ExerciseRepository

    exercise_repo = ExerciseRepository()
    if exercise_repo.count_images(db, exercise_id) >= 5:
        raise BusinessError("VALIDATION_ERROR", "Limite de 5 mídias por exercício.", 400)

    content = await file.read()
    filename = file.filename or "media.bin"
    content_type = (file.content_type or "").lower()

    ext, media_type = _classify_exercise_media(content, filename, content_type)

    relative_dir = Path("exercises") / exercise_id
    absolute_dir = Path(settings.upload_dir) / relative_dir
    _ensure_dir(absolute_dir)

    stored_filename = f"{generate_uuid()}.{ext}"
    relative_path = str(relative_dir / stored_filename)
    (Path(settings.upload_dir) / relative_path).write_bytes(content)

    media = exercise_repo.add_image(
        db,
        exercise_id,
        relative_path.replace("\\", "/"),
        original_filename=file.filename,
        sort_order=sort_order,
        media_type=media_type,
    )
    db.commit()

    return {
        "id": media.id,
        "url": f"/api/v1/uploads/{media.file_path}",
        "media_type": media_type,
        "original_filename": media.original_filename,
        "sort_order": media.sort_order,
        "is_featured": media.is_featured,
    }


# Alias retrocompatível
save_exercise_image = save_exercise_media
