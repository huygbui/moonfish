"""update to use enum instead

Revision ID: b3a6ea4c14e2
Revises: 7939989826ff
Create Date: 2025-06-07 14:01:07.848495

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3a6ea4c14e2"
down_revision: Union[str, None] = "7939989826ff"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


length_enum = sa.Enum("short", "medium", "long", name="length")
level_enum = sa.Enum("beginner", "intermediate", "advanced", name="level")
format_enum = sa.Enum("narrative", "conversational", name="format")
voice_enum = sa.Enum("male", "female", name="voice")
status_enum = sa.Enum("pending", "active", "completed", "cancelled", name="status")
step_enum = sa.Enum("research", "compose", "voice", name="step")


def upgrade() -> None:
    """Upgrade schema."""
    # Step 1: Create the new ENUM types in the database
    length_enum.create(op.get_bind())
    level_enum.create(op.get_bind())
    format_enum.create(op.get_bind())
    voice_enum.create(op.get_bind())
    status_enum.create(op.get_bind())
    step_enum.create(op.get_bind())

    # Step 2: Alter the columns to use the new types
    # The 'postgresql_using' argument tells PG how to cast the old VARCHAR data to the new ENUM type.
    op.alter_column(
        "podcast",
        "length",
        existing_type=sa.VARCHAR(),
        type_=length_enum,
        existing_nullable=False,
        postgresql_using="length::text::length",
    )

    op.alter_column(
        "podcast",
        "level",
        existing_type=sa.VARCHAR(),
        type_=level_enum,
        existing_nullable=False,
        postgresql_using="level::text::level",
    )

    op.alter_column(
        "podcast",
        "format",
        existing_type=sa.VARCHAR(),
        type_=format_enum,
        existing_nullable=False,
        postgresql_using="format::text::format",
    )

    op.alter_column(
        "podcast",
        "voice",
        existing_type=sa.VARCHAR(),
        type_=voice_enum,
        existing_nullable=False,
        postgresql_using="voice::text::voice",
    )

    op.alter_column(
        "podcast",
        "status",
        existing_type=sa.VARCHAR(),
        type_=status_enum,
        existing_nullable=False,
        postgresql_using="status::text::status",
    )

    op.alter_column(
        "podcast",
        "step",
        existing_type=sa.VARCHAR(),
        type_=step_enum,
        existing_nullable=True,
        postgresql_using="step::text::step",
    )


def downgrade() -> None:
    """Downgrade schema."""
    # In downgrade, we do the reverse: alter columns first, then drop types.

    # Step 1: Alter columns back to VARCHAR
    op.alter_column(
        "podcast", "step", type_=sa.VARCHAR(), existing_type=step_enum, existing_nullable=True
    )
    op.alter_column(
        "podcast", "status", type_=sa.VARCHAR(), existing_type=status_enum, existing_nullable=False
    )
    op.alter_column(
        "podcast", "voice", type_=sa.VARCHAR(), existing_type=voice_enum, existing_nullable=False
    )
    op.alter_column(
        "podcast", "format", type_=sa.VARCHAR(), existing_type=format_enum, existing_nullable=False
    )
    op.alter_column(
        "podcast", "level", type_=sa.VARCHAR(), existing_type=level_enum, existing_nullable=False
    )
    op.alter_column(
        "podcast", "length", type_=sa.VARCHAR(), existing_type=length_enum, existing_nullable=False
    )

    # Step 2: Drop the ENUM types from the database
    length_enum.drop(op.get_bind())
    level_enum.drop(op.get_bind())
    format_enum.drop(op.get_bind())
    voice_enum.drop(op.get_bind())
    status_enum.drop(op.get_bind())
    step_enum.drop(op.get_bind())
