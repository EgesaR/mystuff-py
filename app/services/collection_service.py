"""Business logic for collections — cross-folder file groupings."""

from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models.collection import Collection
from app.models.file import File
from app.repositories.collection_repository import CollectionRepository
from app.repositories.file_repository import FileRepository
from app.schemas.collection import CollectionResponse
from app.schemas.file import FileResponse


class CollectionService:
    """Service layer for collection CRUD and file membership."""

    @staticmethod
    def to_response(
        db: Session,
        collection: Collection,
    ) -> CollectionResponse:
        """Convert a Collection ORM object into a response schema."""
        return CollectionResponse(
            id=collection.id,
            name=collection.name,
            color=collection.color,
            owner_id=collection.owner_id,
            file_count=CollectionRepository.file_count(db, collection.id),
            created_at=collection.created_at,
            updated_at=collection.updated_at,
        )

    @staticmethod
    def list_collections(
        db: Session,
        user_id: str,
    ) -> list[CollectionResponse]:
        collections = CollectionRepository.get_user_collections(db, user_id)
        return [CollectionService.to_response(db, c) for c in collections]

    @staticmethod
    def create_collection(
        db: Session,
        user_id: str,
        name: str,
        color: str,
    ) -> Collection:
        return CollectionRepository.create(
            db,
            {
                "name": name,
                "color": color,
                "owner_id": user_id,
            },
        )

    @staticmethod
    def get_collection(
        db: Session,
        collection_id: str,
        user_id: str,
    ) -> Collection:
        collection = CollectionRepository.get_user_collection(
            db,
            collection_id,
            user_id,
        )

        if collection is None:
            raise NotFoundError("Collection not found")

        return collection

    @staticmethod
    def update_collection(
        db: Session,
        collection_id: str,
        user_id: str,
        data: dict[str, Any],
    ) -> Collection:
        collection = CollectionService.get_collection(
            db,
            collection_id,
            user_id,
        )

        return CollectionRepository.update(
            db,
            db_obj=collection,
            update_data=data,
        )

    @staticmethod
    def delete_collection(
        db: Session,
        collection_id: str,
        user_id: str,
    ) -> None:
        collection = CollectionService.get_collection(
            db,
            collection_id,
            user_id,
        )

        CollectionRepository.delete(db, db_obj=collection)

    @staticmethod
    def list_files(
        db: Session,
        collection_id: str,
        user_id: str,
    ) -> list[FileResponse]:
        """Return all files in a collection as response schemas."""

        CollectionService.get_collection(
            db,
            collection_id,
            user_id,
        )

        files: list[File] = CollectionRepository.get_files(
            db,
            collection_id,
        )

        return [
            FileResponse.model_validate(file)
            for file in files
        ]

    @staticmethod
    def add_file(
        db: Session,
        collection_id: str,
        file_id: str,
        user_id: str,
    ) -> None:
        CollectionService.get_collection(
            db,
            collection_id,
            user_id,
        )

        file = FileRepository.get_user_file(
            db,
            file_id=file_id,
            user_id=user_id,
        )

        if file is None:
            raise NotFoundError("File not found")

        CollectionRepository.add_file(
            db,
            collection_id,
            file_id,
        )

    @staticmethod
    def remove_file(
        db: Session,
        collection_id: str,
        file_id: str,
        user_id: str,
    ) -> None:
        CollectionService.get_collection(
            db,
            collection_id,
            user_id,
        )

        CollectionRepository.remove_file(
            db,
            collection_id,
            file_id,
        )

    @staticmethod
    def get_file_collections(
        db: Session,
        file_id: str,
        user_id: str,
    ) -> list[Collection]:
        return CollectionRepository.get_file_collections(
            db,
            file_id,
            user_id,
        )
