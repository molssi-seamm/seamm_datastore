"""remove path, add flowchart_metadata field from flowchart table

Revision ID: 7b24598d1fee
Revises:
Create Date: 2022-03-24 19:20:10.341379

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "7b24598d1fee"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    try:
        op.add_column("flowcharts", sa.Column("conceptdoi", sa.Text(), nullable=True))
    except Exception:
        pass
    try:
        op.add_column(
            "flowcharts", sa.Column("flowchart_metadata", sa.JSON(), nullable=True)
        )
    except Exception:
        pass
    try:
        op.drop_column("flowcharts", "path")
    except Exception:
        pass
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("flowcharts", sa.Column("path", sa.VARCHAR(), nullable=True))
    op.drop_column("flowcharts", "flowchart_metadata")
    op.drop_column("flowcharts", "conceptdoi")
    # ### end Alembic commands ###