import sqlalchemy as sa
from sqlalchemy import event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.schema import UniqueConstraint

from src.database import Base, engine
from src.source import Source
from sqlalchemy import orm, func

from src.utils import legalize

utcnow = func.timezone("UTC", func.current_timestamp())


class Properties(Base):

    __tablename__ = "properties"

    __table_args__ = (
        UniqueConstraint(
            "source_name",
            "project",
            "cfg_hash",
            name="_properties_source_name_in_project_uc",
        ),
    )

    def __setattr__(self, key, value):
        if key == "project" and value is not None:
            value = legalize(value)
        if key == "source" and value is not None:
            self.source_name = value.name

        super().__setattr__(key, value)

    source_id = sa.Column(
        sa.ForeignKey("sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID of the source these properties are associated with",
    )

    source = orm.relationship(
        "Source",
        back_populates="properties",
        cascade="save-update, merge, expunge, refresh-expire",
        foreign_keys="Properties.source_id",
    )

    # source_name = association_proxy("source", "name")

    source_name = sa.Column(
        sa.String,
        nullable=False,
        index=True,
        doc="Name of the source these properties are associated with",
    )

    project = sa.Column(
        sa.String,
        nullable=False,
        index=True,
        doc="Project these properties are associated with",
    )

    cfg_hash = sa.Column(
        sa.String,
        nullable=False,
        index=True,
        default="",
        doc="Hash of the configuration used to generate this object."
        "(leave empty if not using version control)",
    )

    props = sa.Column(
        JSONB,
        nullable=False,
        default={},
        doc="Properties of the source",
    )

    has_data = sa.Column(
        sa.Boolean,
        nullable=False,
        index=True,
        default=True,
        doc="A source with empty datasets would have no "
        "usable properties but still needs to have a "
        "Properties object so we don't re-analyze it.",
    )


Source.properties = orm.relationship(
    "Properties",
    back_populates="source",
    cascade="save-update, merge, refresh-expire, expunge, delete, delete-orphan",
    lazy="selectin",
    single_parent=True,
    uselist=False,
    passive_deletes=True,
    doc="Properties associated with this source",
)


Properties.metadata.create_all(engine)


@event.listens_for(Properties, "before_insert")
def insert_new_dataset(mapper, connection, target):
    """
    Make sure Properties that are added to the DB get
    a source_name a project and a cfg_hash.
    """

    if target.source_name is None or target.project is None or target.cfg_hash is None:
        source = None
        if target.source is not None:
            source = target.source
        if source is None and target.source_id is not None:
            source = connection.scalars(
                sa.select(Source).where(Source.id == target.source_id)
            ).first()
            if source is None:
                raise ValueError(f"Source with ID {target.source_id} does not exist. ")

        if source is None:
            raise ValueError(
                f"Cannot post a Properties object without an associated Source. "
            )

        target.source_name = source.name
        target.project = source.project
        target.cfg_hash = source.cfg_hash
