"""first table init

Revision ID: 62627e9e6b0f
Revises: 
Create Date: 2025-07-04 19:49:26.762718

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '62627e9e6b0f'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('user',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('apple_id', sa.String(), nullable=True),
    sa.Column('email', sa.String(), nullable=True),
    sa.Column('name', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_apple_id'), 'user', ['apple_id'], unique=True)
    op.create_table('podcast',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(), nullable=False),
    sa.Column('format', sa.Enum('narrative', 'conversational', name='format'), nullable=False),
    sa.Column('voice1', sa.Enum('male', 'female', name='voice'), nullable=False),
    sa.Column('name1', sa.String(), nullable=True),
    sa.Column('voice2', sa.Enum('male', 'female', name='voice'), nullable=True),
    sa.Column('name2', sa.String(), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('image_path', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_podcast_user_id'), 'podcast', ['user_id'], unique=False)
    op.create_table('episode',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('topic', sa.String(), nullable=False),
    sa.Column('length', sa.Enum('short', 'medium', 'long', name='length'), nullable=False),
    sa.Column('level', sa.Enum('beginner', 'intermediate', 'advanced', name='level'), nullable=False),
    sa.Column('format', sa.Enum('narrative', 'conversational', name='format'), nullable=False),
    sa.Column('voice1', sa.Enum('male', 'female', name='voice'), nullable=False),
    sa.Column('name1', sa.String(), nullable=True),
    sa.Column('voice2', sa.Enum('male', 'female', name='voice'), nullable=True),
    sa.Column('name2', sa.String(), nullable=True),
    sa.Column('instruction', sa.Text(), nullable=True),
    sa.Column('status', sa.Enum('pending', 'active', 'completed', 'cancelled', 'failed', name='status'), nullable=False),
    sa.Column('step', sa.Enum('research', 'compose', 'voice', name='step'), nullable=True),
    sa.Column('hatchet_run_id', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('podcast_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['podcast_id'], ['podcast.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_episode_podcast_id'), 'episode', ['podcast_id'], unique=False)
    op.create_index(op.f('ix_episode_user_id'), 'episode', ['user_id'], unique=False)
    op.create_table('episode_audio',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('file_name', sa.String(), nullable=False),
    sa.Column('duration', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('episode_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['episode_id'], ['episode.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_episode_audio_episode_id'), 'episode_audio', ['episode_id'], unique=False)
    op.create_table('episode_content',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(), nullable=False),
    sa.Column('summary', sa.Text(), nullable=False),
    sa.Column('transcript', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('episode_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['episode_id'], ['episode.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_episode_content_episode_id'), 'episode_content', ['episode_id'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_episode_content_episode_id'), table_name='episode_content')
    op.drop_table('episode_content')
    op.drop_index(op.f('ix_episode_audio_episode_id'), table_name='episode_audio')
    op.drop_table('episode_audio')
    op.drop_index(op.f('ix_episode_user_id'), table_name='episode')
    op.drop_index(op.f('ix_episode_podcast_id'), table_name='episode')
    op.drop_table('episode')
    op.drop_index(op.f('ix_podcast_user_id'), table_name='podcast')
    op.drop_table('podcast')
    op.drop_index(op.f('ix_user_apple_id'), table_name='user')
    op.drop_table('user')
    # ### end Alembic commands ###
