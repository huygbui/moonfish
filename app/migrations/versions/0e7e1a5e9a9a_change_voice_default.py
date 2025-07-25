"""change voice from gender to names

Revision ID: 0e7e1a5e9a9a
Revises: 64be83e3d711
Create Date: 2025-07-25 09:29:40.103938
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0e7e1a5e9a9a"
down_revision: Union[str, None] = "64be83e3d711"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create new enum type
    op.execute("CREATE TYPE voice_new AS ENUM ('maya', 'jake', 'sofia', 'alex')")

    # Handle both episode and podcast tables
    tables = ["episode", "podcast"]

    for table in tables:
        # Add temporary columns with new enum type
        op.add_column(
            table,
            sa.Column(
                "voice1_temp",
                sa.Enum("maya", "jake", "sofia", "alex", name="voice_new"),
                nullable=True,
            ),
        )
        op.add_column(
            table,
            sa.Column(
                "voice2_temp",
                sa.Enum("maya", "jake", "sofia", "alex", name="voice_new"),
                nullable=True,
            ),
        )

        # Migrate data from old to new columns with explicit casting
        op.execute(f"""
            UPDATE {table}
            SET voice1_temp = CASE
                WHEN voice1 = 'female' THEN 'maya'::voice_new
                WHEN voice1 = 'male' THEN 'jake'::voice_new
                ELSE 'maya'::voice_new
            END,
            voice2_temp = CASE
                WHEN voice2 = 'female' THEN 'sofia'::voice_new
                WHEN voice2 = 'male' THEN 'alex'::voice_new
                WHEN voice2 IS NULL THEN NULL
            END
        """)

        # Drop the old columns
        op.drop_column(table, "voice1")
        op.drop_column(table, "voice2")

        # Rename the temporary columns to the original names
        op.alter_column(table, "voice1_temp", new_column_name="voice1")
        op.alter_column(table, "voice2_temp", new_column_name="voice2")

        # Set the correct nullable constraints
        op.alter_column(table, "voice1", nullable=False)
        # voice2 is already nullable, so no change needed

    # Now we can safely drop the old enum type since no columns reference it
    op.execute("DROP TYPE voice")

    # Rename the new enum type to the original name
    op.execute("ALTER TYPE voice_new RENAME TO voice")


def downgrade() -> None:
    """Downgrade schema."""
    # Create old enum type
    op.execute("CREATE TYPE voice_old AS ENUM ('male', 'female')")

    # Handle both episode and podcast tables
    tables = ["episode", "podcast"]

    for table in tables:
        # Add temporary columns with old enum type
        op.add_column(
            table,
            sa.Column("voice1_temp", sa.Enum("male", "female", name="voice_old"), nullable=True),
        )
        op.add_column(
            table,
            sa.Column("voice2_temp", sa.Enum("male", "female", name="voice_old"), nullable=True),
        )

        # Migrate data back from new to old columns with explicit casting
        op.execute(f"""
            UPDATE {table}
            SET voice1_temp = CASE
                WHEN voice1 IN ('maya', 'sofia') THEN 'female'::voice_old
                WHEN voice1 IN ('jake', 'alex') THEN 'male'::voice_old
                ELSE 'female'::voice_old
            END,
            voice2_temp = CASE
                WHEN voice2 IN ('maya', 'sofia') THEN 'female'::voice_old
                WHEN voice2 IN ('jake', 'alex') THEN 'male'::voice_old
                WHEN voice2 IS NULL THEN NULL
            END
        """)

        # Drop the new columns
        op.drop_column(table, "voice1")
        op.drop_column(table, "voice2")

        # Rename the temporary columns to the original names
        op.alter_column(table, "voice1_temp", new_column_name="voice1")
        op.alter_column(table, "voice2_temp", new_column_name="voice2")

        # Set the correct nullable constraints
        op.alter_column(table, "voice1", nullable=False)
        # voice2 remains nullable

    # Drop the new enum type
    op.execute("DROP TYPE voice")

    # Rename the old enum type to the original name
    op.execute("ALTER TYPE voice_old RENAME TO voice")
