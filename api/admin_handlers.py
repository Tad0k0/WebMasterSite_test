from fastapi import APIRouter
from fastapi import Request
from fastapi import Form
from fastapi.encoders import jsonable_encoder
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from datetime import datetime
from itertools import groupby

from db.session import async_session
from api.actions.urls import _get_urls_with_pagination

admin_router = APIRouter()

templates = Jinja2Templates(directory="static")


def pad_list_with_zeros(lst, amount):
    if len(lst) < amount:
        padding = [f"<div style='height: 55px; width: 100px'>0</div>"] * (amount - len(lst))
        lst.extend(padding)
    return lst


@admin_router.post("/get")
async def get_urls(request: Request, length: int = Form(), start: int = Form(), start_date: datetime = Form(default=""),
                   end_date: datetime = Form(default=""), amount: int = Form()):
    print(start_date)
    print(end_date)
    limit = length
    offset = start + 1
    urls = await _get_urls_with_pagination(offset, limit, start_date, end_date, async_session)
    try:
        grouped_data = [(key, sorted(list(group)[:14], key=lambda x: x[0])) for key, group in
                        groupby(urls, key=lambda x: x[-1])]
    except TypeError as e:
        print(urls)
        return
    if len(grouped_data) == 0:
        return {"data": []}
    data = []
    for el in grouped_data:
        res = [
            f"<div style='width:355px; height: 55px; overflow: auto; white-space: nowrap;'><span>{el[0]}</span></div>"]
        for stat in el[1]:
            res.append(f"""<div style='height: 55px; width: 100px; margin: 0px; padding: 0px'>
            <span style='font-size: 18px'>{stat[1]}</span><br>
            <span style='font-size: 10px'>Клики</span><span style='font-size: 10px; margin-left: 20px'>CTR {stat[4]}%</span><br>
            <span style='font-size: 10px'>{stat[2]}</span> <span style='font-size: 10px; margin-left: 45px'>R {stat[3]}%</span>
            </div>""")
        res = pad_list_with_zeros(res, amount + 1)
        data.append(res)
    json_data = jsonable_encoder(data)

    return JSONResponse({"data": json_data, "recordsTotal": limit, "recordsFiltered": 50000})


@admin_router.get("/info-urls")
async def get_urls(request: Request):
    response = templates.TemplateResponse("urls-info.html", {"request": request})
    return response
