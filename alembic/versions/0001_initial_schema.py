"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-17

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=32), server_default="operator", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.CheckConstraint("role IN ('operator', 'admin')", name="ck_users_role"),
    )

    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    op.create_table(
        "labels",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("color", sa.String(length=7), server_default="#6b7280", nullable=False),
        sa.UniqueConstraint("name", name="uq_labels_name"),
        sa.CheckConstraint("color ~ '^#[0-9A-Fa-f]{6}$'", name="ck_labels_color_format"),
    )

    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("assignee_id", sa.Integer(), nullable=True),
        sa.Column("label_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="open", nullable=False),
        sa.Column("priority", sa.String(length=16), server_default="medium", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name="fk_tasks_project_id", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["assignee_id"], ["users.id"], name="fk_tasks_assignee_id", ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["label_id"], ["labels.id"], name="fk_tasks_label_id", ondelete="SET NULL"
        ),
        sa.CheckConstraint("status IN ('open', 'in_progress', 'done')", name="ck_tasks_status"),
        sa.CheckConstraint("priority IN ('low', 'medium', 'high')", name="ck_tasks_priority"),
    )
    op.create_index("ix_tasks_project_id", "tasks", ["project_id"])
    op.create_index("ix_tasks_assignee_id", "tasks", ["assignee_id"])
    op.create_index("ix_tasks_label_id", "tasks", ["label_id"])

    op.create_table(
        "comments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["task_id"], ["tasks.id"], name="fk_comments_task_id", ondelete="CASCADE"
        ),
        # Пользователя с комментариями удалить нельзя.
        sa.ForeignKeyConstraint(
            ["author_id"], ["users.id"], name="fk_comments_author_id", ondelete="RESTRICT"
        ),
        sa.CheckConstraint("length(btrim(body)) > 0", name="ck_comments_body_not_empty"),
    )
    op.create_index("ix_comments_task_id", "comments", ["task_id"])
    op.create_index("ix_comments_author_id", "comments", ["author_id"])

    # updated_at заполняет сама БД при каждом UPDATE задачи.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION set_tasks_updated_at() RETURNS trigger AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_tasks_set_updated_at
        BEFORE UPDATE ON tasks
        FOR EACH ROW EXECUTE FUNCTION set_tasks_updated_at();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_tasks_set_updated_at ON tasks")
    op.execute("DROP FUNCTION IF EXISTS set_tasks_updated_at()")
    op.drop_table("comments")
    op.drop_table("tasks")
    op.drop_table("labels")
    op.drop_table("projects")
    op.drop_table("users")
