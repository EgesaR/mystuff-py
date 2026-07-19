"""Repository for collections and their file membership."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.collection import Collection, CollectionFile
from app.models.file import File


class CollectionRepository:
    """Data-access methods for collections and collection membership."""

    @staticmethod
    def create(db: Session, obj_in: dict[str, Any]) -> Collection:
        collection = Collection(**obj_in)
        db.add(collection)
        db.commit()
        db.refresh(collection)
        return collection

    @staticmethod
    def get(db: Session, collection_id: str) -> Collection | None:
        return db.get(Collection, collection_id)

    @staticmethod
    def get_user_collection(
        db: Session, collection_id: str, user_id: str
    ) -> Collection | None:
        stmt = select(Collection).where(
            Collection.id == collection_id, Collection.owner_id == user_id
        )
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def get_user_collections(db: Session, user_id: str) -> list[Collection]:
        stmt = (
            select(Collection)
            .where(Collection.owner_id == user_id)
            .order_by(Collection.name)
        )
        return list(db.execute(stmt).scalars().all())

    @staticmethod
    def update(
        db: Session, 
        db_obj: Collection, 
        update_data: dict[str, Any]
    ) -> Collection:
        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    @staticmethod
    def delete(db: Session, db_obj: Collection) -> None:
        db.delete(db_obj)
        db.commit()

    @staticmethod
    def get_files(db: Session, collection_id: str) -> list[File]:
        stmt = (
            select(File)
            .join(CollectionFile, CollectionFile.file_id == File.id)
            .where(CollectionFile.collection_id == collection_id)
            .order_by(File.name)
        )
        return list(db.execute(stmt).scalars().all())

    @staticmethod
    def file_count(db: Session, collection_id: str) -> int:
        stmt = select(CollectionFile).where(
            CollectionFile.collection_id == collection_id
        )
        return len(list(db.execute(stmt).scalars().all()))

    @staticmethod
    def is_member(db: Session, collection_id: str, file_id: str) -> bool:
        stmt = select(CollectionFile).where(
            CollectionFile.collection_id == collection_id,
            CollectionFile.file_id == file_id,
        )
        return db.execute(stmt).scalar_one_or_none() is not None

    @staticmethod
    def add_file(db: Session, collection_id: str, file_id: str) -> CollectionFile | None:
        """Add a file to a collection. Idempotent — returns None (no-op) if
        the file is already a member instead of raising a unique-constraint
        error, since "add to collection" is naturally a toggle-safe action.
        """
        if CollectionRepository.is_member(db, collection_id, file_id):
            return None
        link = CollectionFile(collection_id=collection_id, file_id=file_id)
        db.add(link)
        db.commit()
        return link

    @staticmethod
    def remove_file(db: Session, collection_id: str, file_id: str) -> bool:
        stmt = select(CollectionFile).where(
            CollectionFile.collection_id == collection_id,
            CollectionFile.file_id == file_id,
        )
        link = db.execute(stmt).scalar_one_or_none()
        if not link:
            return False
        db.delete(link)
        db.commit()
        return True

    @staticmethod
    def get_file_collections(
        db: Session, file_id: str, user_id: str
    ) -> list[Collection]:
        stmt = (
            select(Collection)
            .join(CollectionFile, CollectionFile.collection_id == Collection.id)
            .where(CollectionFile.file_id == file_id, Collection.owner_id == user_id)
        )
        return list(db.execute(stmt).scalars().all())
