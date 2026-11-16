
"""Authentication business logic for TripMate AI."""

from app.core.security import hash_password, verify_password
from app.db.models.user import User
from app.repositories.audit_repository import AuditRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import UserLogin, UserRegister


class AuthService:
    """Handle user registration and credential verification."""

    def __init__(self, repository: UserRepository) -> None:
        self.repository = repository
        self.db = repository.db
        self.audit_repository = AuditRepository(self.db)

    def register(self, payload: UserRegister) -> User:
        """Register a user and audit the operation atomically."""
        email = payload.email.strip().lower()

        if self.repository.email_exists(email):
            raise ValueError("A user with this email address already exists")

        password_hash = hash_password(payload.password)

        try:
            user = self.repository.create(
                email=email,
                display_name=payload.display_name,
                password_hash=password_hash,
            )

            self.audit_repository.record_event(
                actor_user_id=user.id,
                action="user.registered",
                entity_type="user",
                entity_id=user.id,
                details={},
            )

            self.db.commit()
            self.db.refresh(user)
            return user

        except Exception:
            self.db.rollback()
            raise

    def authenticate(self, payload: UserLogin) -> User | None:
        """Verify credentials and return the active user, if valid."""
        user = self.repository.get_by_email(payload.email)

        # Return the same public result for unknown users and bad passwords.
        if user is None or user.password_hash is None:
            return None

        if not verify_password(payload.password, user.password_hash):
            return None

        if not user.is_active:
            return None

        return user
