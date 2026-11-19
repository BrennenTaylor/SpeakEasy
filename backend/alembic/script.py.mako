"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
"""

from collections.abc import Sequence
% if upgrades or downgrades:

import sqlalchemy as sa
from alembic import op
% endif
${imports if imports else ""}
revision: str = ${f'"{up_revision}"' if up_revision else "None"}
down_revision: str | None = ${f'"{down_revision}"' if down_revision else "None"}
branch_labels: str | Sequence[str] | None = ${repr(branch_labels)}
depends_on: str | Sequence[str] | None = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
