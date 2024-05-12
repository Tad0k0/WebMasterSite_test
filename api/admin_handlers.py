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
from api.actions.urls import _get_urls_with_pagination_and_like

admin_router = APIRouter()

templates = Jinja2Templates(directory="static")


def pad_list_with_zeros(lst, amount):
    if len(lst) < amount:
        padding = [f"""<div style='height: 55px; width: 100px; margin: 0px; padding: 0px; background-color: #B9BDBC'>
            <span style='font-size: 18px'><span style='color:red'>NAN</span></span><br>
            <span style='font-size: 10px'>Клики</span><span style='font-size: 10px; margin-left: 20px'>CTR <span style='color:red'>NAN%</span></span><br>
            <span style='font-size: 10px'><span style='color:red'>NAN</span></span> <span style='font-size: 10px; margin-left: 30px'>R <span style='color:red'>NAN%</span></span>
            </div>"""] * (amount - len(lst))
        lst.extend(padding)
    return lst


@admin_router.post("/get")
async def get_urls(request: Request, length: int = Form(), start: int = Form(), start_date: datetime = Form(),
                   end_date: datetime = Form(), amount: int = Form(default=14), search_text: str = Form(default=""), \
                   sort_result: bool = Form(default=False), sort_desc: bool = Form(default=False)):
    print(sort_result, sort_desc)
    limit = length
    offset = start + 1
    if search_text == "":
        urls = await _get_urls_with_pagination(offset, limit, start_date, end_date, async_session)
    else:
        urls = await _get_urls_with_pagination_and_like(offset, limit, start_date, end_date, search_text, async_session)
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
        for k, stat in enumerate(el[1]):
            up = 0
            if k + 1 < len(el[1]):
                up = round(el[1][k + 1][1] - el[1][k][1], 2)
            if up > 0:
                color = "#9DE8BD"
                color_text = "green"
            elif up < 0:
                color = "#FDC4BD"
                color_text = "red"
            else:
                color = "#B4D7ED"
                color_text = "black"
            res.append(f"""<div style='height: 55px; width: 100px; margin: 0px; padding: 0px; background-color: {color}'>
            <span style='font-size: 18px'>{stat[1]}</span><span style="margin-left: 5px; font-size: 10px; color: {color_text}">{abs(up)}</span><br>
            <span style='font-size: 10px'>Клики</span><span style='font-size: 10px; margin-left: 20px'>CTR {stat[4]}%</span><br>
            <span style='font-size: 10px'>{stat[2]}</span> <span style='font-size: 10px; margin-left: 45px'>R {stat[3]}%</span>
            </div>""")
        res = pad_list_with_zeros(res, amount + 1)
        data.append(res)
    print("Amount: ", amount)
    print("Amount columns: ", len(data[0]))
    json_data = jsonable_encoder(data)

    # return JSONResponse({"data": json_data, "recordsTotal": limit, "recordsFiltered": 50000})
    return JSONResponse({"data": json_data, "recordsTotal": limit})


@admin_router.get("/info-urls")
async def get_urls(request: Request):
    response = templates.TemplateResponse("urls-info.html", {"request": request})
    return response
