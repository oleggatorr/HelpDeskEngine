class DocumentAttachmentService:

    def __init__(self, db: AsyncSession, storage: FileStorage):
        self.db = db
        self.storage = storage
        logger.debug("DocumentAttachmentService initialized")

    async def upload(
        self,
        document_id: int,
        content: bytes,
        filename: str,
        user_id: int,
        file_type: str | None = None,
    ) -> DocumentAttachment:

        # 1. сохраняем файл
        path = self.storage.save(content, filename)

        try:
            # 2. создаём запись
            attachment = DocumentAttachment(
                document_id=document_id,
                file_path=path,
                original_filename=filename,
                file_type=file_type,
                uploaded_by=user_id,
            )

            self.db.add(attachment)

            # ❗ ВАЖНО: flush вместо commit
            await self.db.flush()

            logger.info(
                f"Attachment prepared: "
                f"document_id={document_id}, file={filename}"
            )

            return attachment

        except Exception as e:
            # ❗ если БД упала → удаляем файл
            logger.error(f"Upload failed, removing file: {path}")

            self.storage.delete(path)
            raise