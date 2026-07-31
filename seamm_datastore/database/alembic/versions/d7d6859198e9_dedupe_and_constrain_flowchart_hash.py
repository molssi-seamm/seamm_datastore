"""dedupe flowcharts.sha256_strict and make it unique

Fixes https://github.com/molssi-seamm/seamm_datastore/issues/37 : concurrent
submission of jobs sharing the same flowchart could race past the
lookup-then-insert in ``Flowchart.create``/``Job.create`` and insert more
than one ``flowcharts`` row for the same ``sha256_strict``. Once that
happens, every later ``.one_or_none()`` lookup by hash raises
``MultipleResultsFound`` and jobs can no longer be registered.

This migration is belt-and-suspenders:

1. Deduplicates any existing rows that already share a (non-null)
   ``sha256_strict`` -- keeping the lowest ``id``, repointing
   ``jobs.flowchart_id`` and the ``flowchart_project`` association rows, and
   deleting the extras.
2. Adds a unique constraint on ``sha256_strict`` (NULLs excepted) so the race
   can no longer create duplicates in the first place.

Revision ID: d7d6859198e9
Revises: 7b24598d1fee
Create Date: 2026-07-31

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "d7d6859198e9"
down_revision = "7b24598d1fee"
branch_labels = None
depends_on = None

CONSTRAINT_NAME = "uq_flowcharts_sha256_strict"


def upgrade():
    bind = op.get_bind()
    metadata = sa.MetaData()
    flowcharts = sa.Table("flowcharts", metadata, autoload_with=bind)
    jobs = sa.Table("jobs", metadata, autoload_with=bind)
    flowchart_project = sa.Table("flowchart_project", metadata, autoload_with=bind)

    rows = bind.execute(
        sa.select(flowcharts.c.id, flowcharts.c.sha256_strict).where(
            flowcharts.c.sha256_strict.isnot(None)
        )
    ).fetchall()

    by_hash = {}
    for flowchart_id, sha256_strict in rows:
        by_hash.setdefault(sha256_strict, []).append(flowchart_id)

    for ids in by_hash.values():
        if len(ids) < 2:
            continue
        ids.sort()
        keep, extras = ids[0], ids[1:]

        # Repoint any jobs that pointed at a duplicate onto the survivor.
        bind.execute(
            jobs.update()
            .where(jobs.c.flowchart_id.in_(extras))
            .values(flowchart_id=keep)
        )

        # Repoint flowchart<->project links onto the survivor, without
        # creating duplicate (flowchart, project) pairs there.
        existing_projects = {
            project_id
            for (project_id,) in bind.execute(
                sa.select(flowchart_project.c.project).where(
                    flowchart_project.c.flowchart == keep
                )
            )
        }
        for extra in extras:
            for (project_id,) in bind.execute(
                sa.select(flowchart_project.c.project).where(
                    flowchart_project.c.flowchart == extra
                )
            ):
                if project_id not in existing_projects:
                    bind.execute(
                        flowchart_project.insert().values(
                            flowchart=keep, project=project_id
                        )
                    )
                    existing_projects.add(project_id)
            bind.execute(
                flowchart_project.delete().where(
                    flowchart_project.c.flowchart == extra
                )
            )

        bind.execute(flowcharts.delete().where(flowcharts.c.id.in_(extras)))

    with op.batch_alter_table("flowcharts") as batch_op:
        batch_op.create_unique_constraint(CONSTRAINT_NAME, ["sha256_strict"])


def downgrade():
    with op.batch_alter_table("flowcharts") as batch_op:
        batch_op.drop_constraint(CONSTRAINT_NAME, type_="unique")
