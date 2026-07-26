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
        """Create.
        
        Args:
            db (Session): Database session.
            obj_in (dict[str, Any]): The obj in.
        
        Returns:
            Collection: Collection result.
        """
        collection = Collection(**obj_in)
        db.add(collection)
        db.commit()
        db.refresh(collection)
        return collection

    @staticmethod
    def get(db: Session, collection_id: str) -> Collection | None:
        """Retrieve.
        
        Args:
            db (Session): Database session.
            collection_id (str): Unique identifier of the collection.
        
        Returns:
            Collection | None: Collection or None.
        """
        return db.get(Collection, collection_id)

    @staticmethod
    def get_user_collection(
        db: Session, collection_id: str, user_id: str
    ) -> Collection | None:
        """Retrieve user collection.
        
        Args:
            db (Session): Database session.
            collection_id (str): Unique identifier of the collection.
            user_id (str): Unique identifier of the user.
        
        Returns:
            Collection | None: Collection or None.
        """
        stmt = select(Collection).where(
            Collection.id == collection_id, Collection.owner_id == user_id
        )
        return db.execute(stmt).scalar_one_or_none()

    @staticmethod
    def get_user_collections(db: Session, user_id: str) -> list[Collection]:
        """Retrieve user collections.
        
        Args:
            db (Session): Database session.
            user_id (str): Unique identifier of the user.
        
        Returns:
            list[Collection]: List of Collection.
        """
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
        """Update.
        
        Args:
            db (Session): Database session.
            db_obj (Collection): The db obj.
            update_data (dict[str, Any]): The update data.
        
        Returns:
            Collection: Collection result.
        """
        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    @staticmethod
    def delete(db: Session, db_obj: Collection) -> None:
        """Delete.
        
        Args:
            db (Session): Database session.
            db_obj (Collection): The db obj.
        
        Returns:
            None: None result.
        """
        db.delete(db_obj)
        db.commit()

    @staticmethod
    def get_files(db: Session, collection_id: str) -> list[File]:
        """Retrieve files.
        
        Args:
            db (Session): Database session.
            collection_id (str): Unique identifier of the collection.
        
        Returns:
            list[File]: List of File.
        """
        stmt = (
            select(File)
            .join(CollectionFile, CollectionFile.file_id == File.id)
            .where(CollectionFile.collection_id == collection_id)
            .order_by(File.name)
        )
        return list(db.execute(stmt).scalars().all())

    @staticmethod
    def file_count(db: Session, collection_id: str) -> int:
        """File count.
        
        Args:
            db (Session): Database session.
            collection_id (str): Unique identifier of the collection.
        
        Returns:
            int: int result.
        """
        stmt = select(CollectionFile).where(
            CollectionFile.collection_id == collection_id
        )
        return len(list(db.execute(stmt).scalars().all()))

    @staticmethod
    def is_member(db: Session, collection_id: str, file_id: str) -> bool:
        """Return whether member.
        
        Args:
            db (Session): Database session.
            collection_id (str): Unique identifier of the collection.
            file_id (str): Unique identifier of the file.
        
        Returns:
            bool: True if successful, False otherwise.
        """
        stmt = select(CollectionFile).where(
            CollectionFile.collection_id == collection_id,
            CollectionFile.file_id == file_id,
        )
        return db.execute(stmt).scalar_one_or_none() is not None

    @staticmethod
    def add_file(db: Session, collection_id: str, file_id: str) -> CollectionFile | None:
        """Add file.
        
        Args:
            db (Session): Database session.
            collection_id (str): Unique identifier of the collection.
            file_id (str): Unique identifier of the file.
        
        Returns:
            CollectionFile | None: CollectionFile or None.
        """
        if CollectionRepository.is_member(db, collection_id, file_id):
            return None
        link = CollectionFile(collection_id=collection_id, file_id=file_id)
        db.add(link)
        db.commit()
        return link

    @staticmethod
    def remove_file(db: Session, collection_id: str, file_id: str) -> bool:
        """Remove file.
        
        Args:
            db (Session): Database session.
            collection_id (str): Unique identifier of the collection.
            file_id (str): Unique identifier of the file.
        
        Returns:
            bool: True if successful, False otherwise.
        """
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
        """Retrieve file collections.
        
        Args:
            db (Session): Database session.
            file_id (str): Unique identifier of the file.
            user_id (str): Unique identifier of the user.
        
        Returns:
            list[Collection]: List of Collection.
        """
        stmt = (
            select(Collection)
            .join(CollectionFile, CollectionFile.collection_id == Collection.id)
            .where(CollectionFile.file_id == file_id, Collection.owner_id == user_id)
        )
        return list(db.execute(stmt).scalars().all())
