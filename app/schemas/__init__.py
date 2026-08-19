from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    RefreshTokenRequest,
    ResetPasswordRequest,
    SignupRequest,
)
from app.schemas.blog import (
    BlogAuthorSummary,
    BlogPostCreate,
    BlogPostResponse,
    BlogPostSummary,
    BlogPostUpdate,
)
from app.schemas.collection import (
    CollectionCreate,
    CollectionFileAdd,
    CollectionResponse,
    CollectionUpdate,
)
from app.schemas.contact import (
    ContactMessageCreate,
    ContactMessageResponse,
)
from app.schemas.docs import (
    DocPageCreate,
    DocPageResponse,
    DocPageSummary,
    DocPageUpdate,
)
from app.schemas.file import FileResponse, FileUploadResponse
from app.schemas.folder import FolderCreate, FolderResponse, FolderUpdate
from app.schemas.media import (
    AudioNoteResponse,
    MediaItemResponse,
    NoteMediaResponse,
)
from app.schemas.note import NoteCreate, NoteResponse, NoteUpdate
from app.schemas.token import TokenPair
from app.schemas.user import UserResponse, UserUpdate

__all__ = [
    # Auth
    "SignupRequest",
    "LoginRequest",
    "RefreshTokenRequest",
    "ForgotPasswordRequest",
    "ForgotPasswordResponse",
    "ResetPasswordRequest",
    "ChangePasswordRequest",
    "TokenPair",

    # User
    "UserResponse",
    "UserUpdate",

    # Folders
    "FolderCreate",
    "FolderUpdate",
    "FolderResponse",

    # Files
    "FileResponse",
    "FileUploadResponse",

    # Notes
    "NoteCreate",
    "NoteUpdate",
    "NoteResponse",
    "NoteMediaResponse",

    # Media
    "AudioNoteResponse",
    "MediaItemResponse",

    # Collections
    "CollectionCreate",
    "CollectionUpdate",
    "CollectionResponse",
    "CollectionFileAdd",

    # Blog
    "BlogAuthorSummary",
    "BlogPostCreate",
    "BlogPostUpdate",
    "BlogPostResponse",
    "BlogPostSummary",

    # Docs
    "DocPageCreate",
    "DocPageUpdate",
    "DocPageResponse",
    "DocPageSummary",

    # Contact
    "ContactMessageCreate",
    "ContactMessageResponse",
]
