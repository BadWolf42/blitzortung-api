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
    OldBoundaryModel,
    BoundaryModel,
    LLRModel,
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
        rad: int,
        bigint: bool = False
    ) -> List[ImpactModel]:
    global connection

    logger.debug('get_data(%i, %f, %f, %i):', since, lat, lon, rad)
    factor = 1 if bigint else 1000000000

    query = 'SELECT DISTINCT'\
    ' time,'\
    ' location[0] as lat,'\
    ' location[1] as lon,'\
    ' CAST('\
    '  earth_distance('\
    '   ll_to_earth(location[0], location[1]),'\
    '   ll_to_earth('+str(lat)+', '+str(lon)+')'\
    '  ) AS INT'\
    ' ) as distance'\
    ' FROM impacts'\
    ' WHERE time > '+str(since * factor)+' AND'\
    '  earth_box(ll_to_earth('+str(lat)+', '+str(lon)+'), '+str(rad)+')'\
    '  @> ll_to_earth(location[0], location[1])'\
    ' ORDER BY time ASC;'

    result = connection.execute(text(query)).fetchall()
    # logger.error('res: %s', repr(result))

    impacts: List[ImpactModel] = []
    for impact in result:
        impacts.append(
            ImpactModel(
                time = round(impact[0] / factor),
                lat = impact[1],
                lon = impact[2],
                distance = impact[3]
            )
        )

    return impacts

# -----------------------------------------------------------------------------
@app.post("/query")
def post_query_v1(
    q: OldBoundaryModel,
    response: Response
) -> List[ResponseEqModel]:
    global connection

    start: int = monotonic_ns()
    res: List[ResponseEqModel] = []
    for eq in q.eqs:
        # Find radius
        rad = (eq.north - eq.south) * 40000 / 360 / 2
        #Limit radius to 5000 km
        if rad > 5000:
            raise HTTPException(
                status_code=422,
                detail = [
                    {
                        "type": "greater_than_equal",
                        "loc": [
                            "body",
                            "eqs",
                            "eqId=" + eq.id,
                            "north, south, est, west"
                        ],
                        "msg": "Area radius shoud be less than 5000 km",
                        "input": rad
                    }
                ]
            )
        # Find eq coords and radius
        lat = eq.south + (eq.north - eq.south) / 2
        lon = eq.west + (eq.est - eq.west) / 2
        impacts = get_data(q.since, lat, lon, rad * 1000, True)
        res.append(ResponseEqModel(id=eq.id, impacts=impacts))
    response.headers["x-computation-ms"] = str((monotonic_ns()-start)/(10**6))
    return res

@app.post("/querynsew")
def post_query_nsew(
    q: BoundaryModel,
    response: Response
) -> List[ResponseEqModel]:
    global connection

    start: int = monotonic_ns()
    res: List[ResponseEqModel] = []
    # since: int = q.since * 100000000                       # TODO limit since
    for eq in q.eqs:
        # Find radius
        rad = (eq.north - eq.south) * 40000 / 360 / 2
        #Limit radius to 5000 km
        if rad > 5000:
            raise HTTPException(
                status_code=422,
                detail = [
                    {
                        "type": "greater_than_equal",
                        "loc": [
                            "body",
                            "eqs",
                            "eqId=" + eq.id,
                            "north, south, est, west"
                        ],
                        "msg": "Area radius shoud be less than 5000 km",
                        "input": rad
                    }
                ]
            )
        # Find eq coords and radius
        lat = eq.south + (eq.north - eq.south) / 2
        lon = eq.west + (eq.est - eq.west) / 2
        impacts = get_data(q.since, lat, lon, rad * 1000)
        res.append(ResponseEqModel(id=eq.id, impacts=impacts))
    response.headers["x-computation-ms"] = str((monotonic_ns()-start)/(10**6))
    return res

@app.post("/queryllr")
def post_query_llr(
    q: LLRModel,
    response: Response
) -> List[ResponseEqModel]:
    global connection

    start: int = monotonic_ns()
    res: List[ResponseEqModel] = []
    # since: int = q.since * 100000000                       # TODO limit since
    for eq in q.eqs:
        lat = eq.lat
        lon = eq.lon
        rad = eq.rad
        impacts = get_data(q.since, lat, lon, rad * 1000)
        res.append(ResponseEqModel(id=eq.id, impacts=impacts))
    response.headers["x-computation-ms"] = str((monotonic_ns()-start)/(10**6))
    return res

@app.post("/v2/query")
def post_query_v2(q: LLRModel, response: Response) -> ResponseModel:
    global connection

    start: int = monotonic_ns()
    eqs: List[ResponseEqModel] = []

    # Get last impact time
    query = 'SELECT time FROM impacts ORDER BY time DESC LIMIT 1;'
    result = connection.execute(text(query)).fetchone()
    since = result[0] // 1000000000

    # Get new impacts since last time
    for eq in q.eqs:
        lat = eq.lat
        lon = eq.lon
        rad = eq.rad
        impacts = get_data(q.since, lat, lon, rad * 1000)
        eqs.append(ResponseEqModel(id=eq.id, impacts=impacts))
    response.headers["x-computation-ms"] = str((monotonic_ns()-start)/(10**6))
    return ResponseModel(since=since, eqs=eqs)


@app.get("/stats")
def get_stats(response: Response):
    global connection

    start: int = monotonic_ns()
    query = 'SELECT * FROM'\
        ' (SELECT COUNT(*) as nb FROM impacts) as nb,'\
        ' (SELECT time, location[0] as lat, location[1] as lon'\
        '  FROM impacts ORDER BY time ASC LIMIT 1) as first,'\
        ' (SELECT time, location[0] as lat, location[1] as lon'\
        '  FROM impacts ORDER BY time DESC LIMIT 1) as last;'
    result = connection.execute(text(query)).fetchone()
    ret = {}
    ret['nb'] = result[0]
    ret['first'] = ImpactModel(
        time = result[1],
        lat = result[2],
        lon = result[3],
        distance = 0
    )
    ret['last'] = ImpactModel(
        time = result[4],
        lat = result[5],
        lon = result[6],
        distance = 0
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
