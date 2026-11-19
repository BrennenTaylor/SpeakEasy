<%!
def format_rev(rev):
    if rev is None:
        return "None"
    if isinstance(rev, str):
        return f'"{rev}"'
    if isinstance(rev, (tuple, list)):
        items = ", ".join(f'"{r}"' for r in rev)
        return f"({items},)" if len(rev) == 1 else f"({items})"
    return repr(rev)
%>"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
${imports if imports else ""}
revision: str = ${format_rev(up_revision)}
down_revision: str | Sequence[str] | None = ${format_rev(down_revision)}
branch_labels: str | Sequence[str] | None = ${format_rev(branch_labels)}
depends_on: str | Sequence[str] | None = ${format_rev(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
