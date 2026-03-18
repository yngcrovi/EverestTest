from db.config.engine import EngineDB
from sqlalchemy import text

class PeopleService:

    def __init__(self, user: str = None, password: str = None):
        self.session = EngineDB().get_engine()

    async def insert_data(self, data: dict | list[dict]) -> None:
        async with self.session as s:
            columns = ', '.join(data.keys() if isinstance(data, dict) else data[0].keys())
            values: str = None
            if isinstance(data, dict):
                values = '(' + ', '.join([f':{key}' for key in data.keys()]) + ')'
            else: 
                part_value: list = []
                for el in data:
                    part_value.append('(' + ', '.join([f':{key}' for key in el.keys()]) + ')')
                values = ', '.join(part_value)
            await s.execute(
                    text(f"""
                        INSERT INTO people ({columns})
                        VALUES {values}
                        ON CONFLICT (id) DO NOTHING;
                    """),
                    data
            )
            await s.commit()