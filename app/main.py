from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import RedirectResponse
from logging import getLogger, DEBUG
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection
from time import monotonic_ns
from typing import List

from .models import (
    ImpactModel,
    QueryModel,
    ResponseModel,
    ResponseEqModel
)
from .utils import LogFilter
from .settings import settings


connection: Connection = None
logger = getLogger('blitzop')


# -----------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    global connection

    logger.info('Starting')
    if settings.debug:
        getLogger().setLevel(DEBUG)
        logger.setLevel(DEBUG)

    # Connect to the database
    engine = create_engine(
        'postgresql://{}:{}@{}:{}/{}'.format(
            settings.postgres_user,
            settings.postgres_password,
            settings.postgres_host,
            settings.postgres_port,
            settings.postgres_database
        )
    )
    connection = engine.connect()
    logger.info('Started')
    yield
    logger.info('Stopping')
    connection.close()
    engine.dispose()
    logger.info('Stopped')

# -----------------------------------------------------------------------------
app = FastAPI(
    title='Blitzortung proxy for Jeedom',
    docs_url='/debug' if settings.debug else None, # Disable docs (Swagger UI)
    redoc_url=None,                               # Disable redoc
    lifespan = lifespan,
)

# -----------------------------------------------------------------------------
def get_data(
        since: int,
        lat: float,
        lon: float,
        rad: int
    ) -> List[ImpactModel]:
    global connection

    logger.debug('get_data(%i, %f, %f, %i):', since, lat, lon, rad)

    query = 'SELECT DISTINCT'\
        '  ts,'\
        '  lat::float / 10000000,'\
        '  lon::float / 10000000'\
        ' FROM impacts'\
        ' WHERE'\
        '  earth_box('\
        '   ll_to_earth('+str(lat)+', '+str(lon)+'), '+str(rad) +\
        '  ) @> location'\
        '  AND ts > '+str(since * 1000000000)+\
        '  AND earth_distance('\
        '   ll_to_earth('+str(lat)+','+str(lon)+'),'\
        '   location) <= '+str(rad) +\
        ' ORDER BY ts ASC;'

    result = connection.execute(text(query)).fetchall()
    # logger.error('res: %s', repr(result))

    impacts: List[ImpactModel] = []
    for impact in result:
        impacts.append(
            ImpactModel(
                time = impact[0] // 1000000000,
                lat = impact[1],
                lon = impact[2]
            )
        )

    return impacts

# -----------------------------------------------------------------------------
@app.post("/v2/query")
def post_query_v2(q: QueryModel, response: Response) -> ResponseModel:
    global connection

    start: int = monotonic_ns()
    eqs: List[ResponseEqModel] = []

    # Get last impact time
    query = 'SELECT ts FROM impacts ORDER BY ts DESC LIMIT 1;'
    result = connection.execute(text(query)).fetchone()
    lastimpact = result[0] // 1000000000

    # Get new impacts since last time
    for eq in q.eqs:
        lat = eq.lat
        lon = eq.lon
        rad = eq.rad
        impacts = get_data(q.since, lat, lon, rad * 1000)
        eqs.append(ResponseEqModel(id=eq.id, impacts=impacts))
    ret = ResponseModel(since=lastimpact, eqs=eqs)
    response.headers["x-computation-ms"] = str((monotonic_ns()-start)/(10**6))
    return ret


@app.get("/stats")
def get_stats(response: Response):
    global connection

    start: int = monotonic_ns()
    query = 'SELECT * FROM'\
        ' (SELECT COUNT(*) FROM impacts) as nb,'\
        ' (SELECT ts, lat::float / 10000000, lon::float / 10000000'\
        '  FROM impacts ORDER BY ts ASC LIMIT 1) as first,'\
        ' (SELECT ts, lat::float / 10000000, lon::float / 10000000'\
        '  FROM impacts ORDER BY ts DESC LIMIT 1) as last;'
    result = connection.execute(text(query)).fetchone()
    ret = {}
    ret['nb'] = result[0]
    ret['first'] = ImpactModel(
        time = result[1],
        lat = result[2],
        lon = result[3]
    )
    ret['last'] = ImpactModel(
        time = result[4],
        lat = result[5],
        lon = result[6]
    )
    response.headers["x-computation-ms"] = str((monotonic_ns()-start)/(10**6))
    return ret

# -----------------------------------------------------------------------------
@app.exception_handler(404)
def other_queries(_, __):
    return RedirectResponse(
        "https://github.com/BisonJeedom/documentations/"\
        "blob/main/blitzortung/index_stable.md"
    )
