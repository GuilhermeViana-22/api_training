def build_upload_url(file_path: str | None) -> str | None:
    if not file_path:
        return None
    return f"/api/v1/uploads/{file_path}"
