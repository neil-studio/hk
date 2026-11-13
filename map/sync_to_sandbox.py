#!/usr/bin/env python3
"""
同步脚本：将 ORS 真实步行路网数据（距离、时长、折线轨迹）全量注入到运营沙盒地图系统中
"""

import json, math, time, os, sys
import requests

SANDBOX_DIR = "/Users/nb/google/Antigravity/工作/运营/价单/sandbox"
COORDS_PATH = os.path.join(SANDBOX_DIR, "hk_project_coords.json")
MAP_HTML_PATH = "/Users/nb/.gemini/antigravity/scratch/hk-property-map/hk_property_mtr_map.html"

ORS_TOKEN = "eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6ImIwNjljZjY4YTgzMDQ1MTY5ZTMwZTZjOGExNDc2ODE3IiwiaCI6Im11cm11cjY0In0="
ORS_BASE = "https://api.openrouteservice.org/v2/directions/foot-walking"

MTR_STATIONS = [
    {"name_en":"Kennedy Town","name_zh":"堅尼地城","lat":22.2814,"lng":114.1286,"lines":["港島綫"]},
    {"name_en":"HKU","name_zh":"香港大學","lat":22.2840,"lng":114.1347,"lines":["港島綫"]},
    {"name_en":"Sai Ying Pun","name_zh":"西營盤","lat":22.2856,"lng":114.1427,"lines":["港島綫"]},
    {"name_en":"Sheung Wan","name_zh":"上環","lat":22.2865,"lng":114.1520,"lines":["港島綫","荃灣綫"]},
    {"name_en":"Central","name_zh":"中環","lat":22.2820,"lng":114.1583,"lines":["港島綫","荃灣綫"]},
    {"name_en":"Admiralty","name_zh":"金鐘","lat":22.2793,"lng":114.1654,"lines":["港島綫","荃灣綫","南港島綫","東鐵綫"]},
    {"name_en":"Wan Chai","name_zh":"灣仔","lat":22.2776,"lng":114.1731,"lines":["港島綫"]},
    {"name_en":"Causeway Bay","name_zh":"銅鑼灣","lat":22.2802,"lng":114.1840,"lines":["港島綫"]},
    {"name_en":"Tin Hau","name_zh":"天后","lat":22.2825,"lng":114.1918,"lines":["港島綫"]},
    {"name_en":"Fortress Hill","name_zh":"炮台山","lat":22.2879,"lng":114.1937,"lines":["港島綫"]},
    {"name_en":"North Point","name_zh":"北角","lat":22.2912,"lng":114.2001,"lines":["港島綫","將軍澳綫"]},
    {"name_en":"Quarry Bay","name_zh":"鰂魚涌","lat":22.2878,"lng":114.2097,"lines":["港島綫","將軍澳綫"]},
    {"name_en":"Tai Koo","name_zh":"太古","lat":22.2845,"lng":114.2165,"lines":["港島綫"]},
    {"name_en":"Sai Wan Ho","name_zh":"西灣河","lat":22.2828,"lng":114.2222,"lines":["港島綫"]},
    {"name_en":"Shau Kei Wan","name_zh":"筲箕灣","lat":22.2790,"lng":114.2283,"lines":["港島綫"]},
    {"name_en":"Heng Fa Chuen","name_zh":"杏花邨","lat":22.2766,"lng":114.2396,"lines":["港島綫"]},
    {"name_en":"Chai Wan","name_zh":"柴灣","lat":22.2649,"lng":114.2371,"lines":["港島綫"]},
    {"name_en":"Tsim Sha Tsui","name_zh":"尖沙咀","lat":22.2973,"lng":114.1726,"lines":["荃灣綫"]},
    {"name_en":"Jordan","name_zh":"佐敦","lat":22.3050,"lng":114.1716,"lines":["荃灣綫"]},
    {"name_en":"Yau Ma Tei","name_zh":"油麻地","lat":22.3131,"lng":114.1708,"lines":["荃灣綫","觀塘綫"]},
    {"name_en":"Mong Kok","name_zh":"旺角","lat":22.3193,"lng":114.1694,"lines":["荃灣綫","觀塘綫"]},
    {"name_en":"Prince Edward","name_zh":"太子","lat":22.3245,"lng":114.1683,"lines":["荃灣綫","觀塘綫"]},
    {"name_en":"Sham Shui Po","name_zh":"深水埗","lat":22.3309,"lng":114.1622,"lines":["荃灣綫"]},
    {"name_en":"Cheung Sha Wan","name_zh":"長沙灣","lat":22.3358,"lng":114.1558,"lines":["荃灣綫"]},
    {"name_en":"Lai Chi Kok","name_zh":"荔枝角","lat":22.3375,"lng":114.1481,"lines":["荃灣綫"]},
    {"name_en":"Mei Foo","name_zh":"美孚","lat":22.3386,"lng":114.1377,"lines":["荃灣綫","屯馬綫"]},
    {"name_en":"Lai King","name_zh":"荔景","lat":22.3483,"lng":114.1263,"lines":["荃灣綫","東涌綫"]},
    {"name_en":"Kwai Fong","name_zh":"葵芳","lat":22.3570,"lng":114.1279,"lines":["荃灣綫"]},
    {"name_en":"Kwai Hing","name_zh":"葵興","lat":22.3632,"lng":114.1313,"lines":["荃灣綫"]},
    {"name_en":"Tai Wo Hau","name_zh":"大窩口","lat":22.3708,"lng":114.1253,"lines":["荃灣綫"]},
    {"name_en":"Tsuen Wan","name_zh":"荃灣","lat":22.3733,"lng":114.1177,"lines":["荃灣綫"]},
    {"name_en":"Whampoa","name_zh":"黃埔","lat":22.3048,"lng":114.1897,"lines":["觀塘綫"]},
    {"name_en":"Ho Man Tin","name_zh":"何文田","lat":22.3094,"lng":114.1830,"lines":["觀塘綫","屯馬綫"]},
    {"name_en":"Kowloon Tong","name_zh":"九龍塘","lat":22.3368,"lng":114.1760,"lines":["東鐵綫","觀塘綫"]},
    {"name_en":"Wong Tai Sin","name_zh":"黃大仙","lat":22.3424,"lng":114.1936,"lines":["觀塘綫"]},
    {"name_en":"Diamond Hill","name_zh":"鑽石山","lat":22.3401,"lng":114.2015,"lines":["觀塘綫","屯馬綫"]},
    {"name_en":"Choi Hung","name_zh":"彩虹","lat":22.3349,"lng":114.2088,"lines":["觀塘綫"]},
    {"name_en":"Kowloon Bay","name_zh":"九龍灣","lat":22.3235,"lng":114.2138,"lines":["觀塘綫"]},
    {"name_en":"Ngau Tau Kok","name_zh":"牛頭角","lat":22.3158,"lng":114.2193,"lines":["觀塘綫"]},
    {"name_en":"Kwun Tong","name_zh":"觀塘","lat":22.3123,"lng":114.2264,"lines":["觀塘綫"]},
    {"name_en":"Lam Tin","name_zh":"藍田","lat":22.3068,"lng":114.2327,"lines":["觀塘綫"]},
    {"name_en":"Yau Tong","name_zh":"油塘","lat":22.2977,"lng":114.2374,"lines":["觀塘綫","將軍澳綫"]},
    {"name_en":"Tiu Keng Leng","name_zh":"調景嶺","lat":22.3046,"lng":114.2527,"lines":["觀塘綫","將軍澳綫"]},
    {"name_en":"Tseung Kwan O","name_zh":"將軍澳","lat":22.3073,"lng":114.2600,"lines":["將軍澳綫"]},
    {"name_en":"Hang Hau","name_zh":"坑口","lat":22.3155,"lng":114.2646,"lines":["將軍澳綫"]},
    {"name_en":"Po Lam","name_zh":"寶琳","lat":22.3228,"lng":114.2581,"lines":["將軍澳綫"]},
    {"name_en":"LOHAS Park","name_zh":"康城","lat":22.2955,"lng":114.2695,"lines":["將軍澳綫"]},
    {"name_en":"Hong Kong","name_zh":"香港","lat":22.2849,"lng":114.1585,"lines":["東涌綫","機場快綫"]},
    {"name_en":"Kowloon","name_zh":"九龍","lat":22.3050,"lng":114.1615,"lines":["東涌綫","機場快綫"]},
    {"name_en":"Olympic","name_zh":"奧運","lat":22.3178,"lng":114.1601,"lines":["東涌綫"]},
    {"name_en":"Nam Cheong","name_zh":"南昌","lat":22.3265,"lng":114.1537,"lines":["東涌綫","屯馬綫"]},
    {"name_en":"Tsing Yi","name_zh":"青衣","lat":22.3584,"lng":114.1074,"lines":["東涌綫","機場快綫"]},
    {"name_en":"Sunny Bay","name_zh":"欣澳","lat":22.3317,"lng":114.0291,"lines":["東涌綫","迪士尼綫"]},
    {"name_en":"Tung Chung","name_zh":"東涌","lat":22.2892,"lng":114.0001,"lines":["東涌綫"]},
    {"name_en":"Ocean Park","name_zh":"海洋公園","lat":22.2489,"lng":114.1743,"lines":["南港島綫"]},
    {"name_en":"Wong Chuk Hang","name_zh":"黃竹坑","lat":22.2480,"lng":114.1680,"lines":["南港島綫"]},
    {"name_en":"Lei Tung","name_zh":"利東","lat":22.2422,"lng":114.1563,"lines":["南港島綫"]},
    {"name_en":"South Horizons","name_zh":"海怡半島","lat":22.2429,"lng":114.1490,"lines":["南港島綫"]},
    {"name_en":"Exhibition Centre","name_zh":"會展","lat":22.2816,"lng":114.1753,"lines":["東鐵綫"]},
    {"name_en":"Hung Hom","name_zh":"紅磡","lat":22.3029,"lng":114.1818,"lines":["東鐵綫","屯馬綫"]},
    {"name_en":"Mong Kok East","name_zh":"旺角東","lat":22.3221,"lng":114.1722,"lines":["東鐵綫"]},
    {"name_en":"Tai Wai","name_zh":"大圍","lat":22.3726,"lng":114.1785,"lines":["東鐵綫","屯馬綫"]},
    {"name_en":"Sha Tin","name_zh":"沙田","lat":22.3827,"lng":114.1876,"lines":["東鐵綫"]},
    {"name_en":"Fo Tan","name_zh":"火炭","lat":22.3955,"lng":114.1984,"lines":["東鐵綫"]},
    {"name_en":"Racecourse","name_zh":"馬場","lat":22.4012,"lng":114.1836,"lines":["東鐵綫"]},
    {"name_en":"University","name_zh":"大學","lat":22.4133,"lng":114.2100,"lines":["東鐵綫"]},
    {"name_en":"Tai Po Market","name_zh":"大埔墟","lat":22.4446,"lng":114.1706,"lines":["東鐵綫"]},
    {"name_en":"Tai Wo","name_zh":"太和","lat":22.4510,"lng":114.1611,"lines":["東鐵綫"]},
    {"name_en":"Fanling","name_zh":"粉嶺","lat":22.4922,"lng":114.1384,"lines":["東鐵綫"]},
    {"name_en":"Sheung Shui","name_zh":"上水","lat":22.5013,"lng":114.1276,"lines":["東鐵綫"]},
    {"name_en":"Lo Wu","name_zh":"羅湖","lat":22.5282,"lng":114.1133,"lines":["東鐵綫"]},
    {"name_en":"Lok Ma Chau","name_zh":"落馬洲","lat":22.5147,"lng":114.0653,"lines":["東鐵綫"]},
    {"name_en":"Wu Kai Sha","name_zh":"烏溪沙","lat":22.4293,"lng":114.2436,"lines":["屯馬綫"]},
    {"name_en":"Ma On Shan","name_zh":"馬鞍山","lat":22.4250,"lng":114.2316,"lines":["屯馬綫"]},
    {"name_en":"Heng On","name_zh":"恆安","lat":22.4178,"lng":114.2256,"lines":["屯馬綫"]},
    {"name_en":"Tai Shui Hang","name_zh":"大水坑","lat":22.4084,"lng":114.2225,"lines":["屯馬綫"]},
    {"name_en":"Shek Mun","name_zh":"石門","lat":22.3884,"lng":114.2086,"lines":["屯馬綫"]},
    {"name_en":"City One","name_zh":"第一城","lat":22.3832,"lng":114.2037,"lines":["屯馬綫"]},
    {"name_en":"Sha Tin Wai","name_zh":"沙田圍","lat":22.3764,"lng":114.1952,"lines":["屯馬綫"]},
    {"name_en":"Che Kung Temple","name_zh":"車公廟","lat":22.3747,"lng":114.1861,"lines":["屯馬綫"]},
    {"name_en":"Hin Keng","name_zh":"顯徑","lat":22.3654,"lng":114.1708,"lines":["屯馬綫"]},
    {"name_en":"Kai Tak","name_zh":"啟德","lat":22.3307,"lng":114.1994,"lines":["屯馬綫"]},
    {"name_en":"Sung Wong Toi","name_zh":"宋皇臺","lat":22.3261,"lng":114.1894,"lines":["屯馬綫"]},
    {"name_en":"To Kwa Wan","name_zh":"土瓜灣","lat":22.3170,"lng":114.1870,"lines":["屯馬綫"]},
    {"name_en":"Austin","name_zh":"柯士甸","lat":22.3040,"lng":114.1667,"lines":["屯馬綫"]},
    {"name_en":"East Tsim Sha Tsui","name_zh":"尖東","lat":22.2949,"lng":114.1751,"lines":["屯馬綫"]},
    {"name_en":"Tsuen Wan West","name_zh":"荃灣西","lat":22.3684,"lng":114.1097,"lines":["屯馬綫"]},
    {"name_en":"Kam Sheung Road","name_zh":"錦上路","lat":22.4348,"lng":114.0684,"lines":["屯馬綫"]},
    {"name_en":"Yuen Long","name_zh":"元朗","lat":22.4461,"lng":114.0352,"lines":["屯馬綫"]},
    {"name_en":"Long Ping","name_zh":"朗屏","lat":22.4477,"lng":114.0255,"lines":["屯馬綫"]},
    {"name_en":"Tin Shui Wai","name_zh":"天水圍","lat":22.4480,"lng":114.0045,"lines":["屯馬綫"]},
    {"name_en":"Siu Hong","name_zh":"兆康","lat":22.4115,"lng":113.9782,"lines":["屯馬綫"]},
    {"name_en":"Tuen Mun","name_zh":"屯門","lat":22.3952,"lng":113.9733,"lines":["屯馬綫"]},
    {"name_en":"Airport","name_zh":"機場","lat":22.3160,"lng":113.9365,"lines":["機場快綫"]},
    {"name_en":"AsiaWorld-Expo","name_zh":"博覽館","lat":22.3207,"lng":113.9418,"lines":["機場快綫"]},
    {"name_en":"Disneyland Resort","name_zh":"迪士尼","lat":22.3153,"lng":114.0451,"lines":["迪士尼綫"]},
]

def dist_m(lat1, lon1, lat2, lon2):
    R = 6371000
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    a = math.sin(dLat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dLon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def ors_walk(from_lat, from_lng, to_lat, to_lng):
    params = {"start": f"{from_lng},{from_lat}", "end": f"{to_lng},{to_lat}"}
    headers = {"Authorization": ORS_TOKEN, "Accept": "application/json, application/geo+json"}
    try:
        resp = requests.get(ORS_BASE, params=params, headers=headers, timeout=12)
        if resp.status_code == 200:
            data = resp.json()
            feat = data["features"][0]
            seg = feat["properties"]["segments"][0]
            return {
                "distance": round(seg["distance"]),
                "duration": round(seg["duration"]),
                "geometry": feat["geometry"]
            }
    except Exception as e:
        pass
    return None

zh_map = {
    '峯':'峰','滙':'汇','灣':'湾','賢':'贤','璽':'玺','號':'号','鑽':'钻',
    '緹':'缇','奧':'奥','譽':'誉','瓏':'珑','晉':'晋','揚':'扬','滶':'滶',
    '薈':'荟','濤':'涛','閣':'阁','爾':'尔','緻':'致','玥':'玥','莊':'庄',
    '園':'园','朗':'朗','凱':'凯','嵐':'岚','雲':'云','嶺':'岭','曦':'曦',
    '迎':'迎','瑧':'瑧','海':'海','匯':'汇','臺':'台','東':'东','南':'南',
    '西':'西','北':'北','中':'中','島':'岛','龍':'龙','啟':'启','德':'德',
    '紅':'红','磡':'磡','鴨':'鸭','脷':'脷','洲':'洲','黃':'黄','竹':'竹',
    '坑':'坑','壽':'寿','臣':'臣','山':'山','頂':'顶','淺':'浅','水':'水',
    '深':'深','跑':'跑','馬':'马','地':'地','渣':'渣','甸':'甸','薄':'薄',
    '扶':'扶','林':'林','仔':'仔','環':'环','土':'土','瓜':'瓜','營':'营',
    '盤':'盘','銅':'铜','鑼':'锣','後':'后','涌':'涌','怡':'怡','太':'太',
    '古':'古','石':'石','塘':'塘','咀':'咀','摩':'摩','星':'星','赤':'赤',
    '柱':'柱','潭':'潭','澳':'澳','座':'座','樓':'楼','期':'期','門':'门',
    '沙':'沙','田':'田','圍':'围','頌':'颂','傲':'傲','華':'华','喆':'喆',
    '寶':'宝','應':'应','悅':'悦','麓':'麓','維':'维','畔':'畔','語':'语',
    '晴':'晴','首':'首','澄':'澄','碧':'碧','瀧':'泷','澐':'沄','學':'学',
    '鑄':'铸','徑':'径','灃':'沣','瀚':'瀚','逸':'逸','雋':'隽','珀':'珀',
    '珏':'珏','溋':'溋','皓':'皓','晟':'晟','囍':'喜','蘊':'蕴','區':'区',
    '雙':'双','羅':'罗','藍':'蓝','賓':'宾','吉':'吉','道':'道','階':'阶',
    '曉':'晓','柏':'柏','澔':'澔','泰':'泰','豐':'丰','遠':'远','街':'街'
}

def norm_name(s):
    if not s: return ''
    import re
    s = s.replace('III', '3').replace('II', '2').replace('I', '1')
    s = s.replace('iii', '3').replace('ii', '2').replace('i', '1')
    s = re.sub(r'[\s\.\‧\・\．\•\-\_\(\)\（\）\,\，\。\、\/\&]', '', s)
    res = ''.join([zh_map.get(ch, ch) for ch in s])
    return res.lower().replace('第', '').replace('期', '').replace('项目', '').replace('residential', '')

def osrm_walk(from_lat, from_lng, to_lat, to_lng):
    url = f'https://router.project-osrm.org/route/v1/foot/{from_lng},{from_lat};{to_lng},{to_lat}?overview=full&geometries=geojson'
    headers = {'User-Agent': 'HKPropertyMap/1.0'}
    try:
        r = requests.get(url, headers=headers, timeout=12)
        if r.status_code == 200:
            data = r.json()
            if data.get('routes'):
                route = data['routes'][0]
                dist_m = round(route['distance'])
                # OSRM public foot profile duration bug: 官方演示接口误按车速返回duration，此处强制使用人行步速 75m/min (4.5 km/h) 重算
                return {
                    'distance': dist_m,
                    'duration': round((dist_m / 75.0) * 60),
                    'geometry': route['geometry']
                }
    except Exception as e:
        pass
    return None

def main():
    print("1️⃣ 加载沙盒项目数据...")
    with open(COORDS_PATH, "r", encoding="utf-8") as f:
        sandbox_projects = json.load(f)
    print(f"   沙盒项目总数: {len(sandbox_projects)}")

    print("2️⃣ 加载 302 个已计算好的 ORS 真实路网数据...")
    with open(MAP_HTML_PATH, "r", encoding="utf-8") as f:
        html_c = f.read()
    
    idx1 = html_c.find("let DATA = ")
    if idx1 != -1:
        idx1 += len("let DATA = ")
    else:
        idx1 = html_c.find("const DATA = ") + len("const DATA = ")
    
    idx2 = html_c.find(";\n\nlet map,", idx1)
    if idx2 == -1: idx2 = html_c.find(";\nlet map,", idx1)
    ors_data = json.loads(html_c[idx1:idx2])
    print(f"   已计算库总数: {len(ors_data)}")

    ors_by_norm = {norm_name(d['name']): d for d in ors_data}

    updated = 0
    calculated_on_fly = 0

    for i, p in enumerate(sandbox_projects):
        p_name = p.get("name", "").strip()
        p_norm = norm_name(p_name)
        p_addr = norm_name(p.get("address", ""))
        p_lat = p.get("lat")
        p_lng = p.get("lng")
        
        # 1. 尝试匹配已有 ORS 结果
        match = None
        if p_norm in ors_by_norm:
            match = ors_by_norm[p_norm]
        else:
            for d in ors_data:
                d_norm = norm_name(d['name'])
                if (p_norm in d_norm or d_norm in p_norm) and len(p_norm) >= 3:
                    match = d
                    break
        
        if not match and p_addr:
            for d in ors_data:
                d_addr = norm_name(d.get('address', ''))
                if d_addr and (p_addr in d_addr or d_addr in p_addr) and len(p_addr) >= 4:
                    match = d
                    break
        
        if not match and p_lat and p_lng:
            closest = min(ors_data, key=lambda d: dist_m(p_lat, p_lng, d['lat'], d['lng']))
            if dist_m(p_lat, p_lng, closest['lat'], closest['lng']) < 120:
                match = closest
        
        if match and match.get("route_geometry"):
            current_mtr = p.get("nearest_mtr") or {}
            w_dist = match.get("walk_distance", current_mtr.get("dist_walk_m"))
            w_dur = match.get("walk_duration", current_mtr.get("walk_time_min"))
            if w_dist and w_dur and w_dur > 0:
                speed_kmh = (w_dist / 1000.0) / (w_dur / 60.0)
                if not (2.5 <= speed_kmh <= 6.5):
                    w_dur = round(w_dist / 75.0, 1)
            p["nearest_mtr"] = {
                "nearest_mtr_id": current_mtr.get("nearest_mtr_id") or f"mtr_{norm_name(match.get('station_en', ''))}",
                "nearest_mtr_name": f"{match.get('station_zh')}站 ({match.get('lines', [''])[0] if match.get('lines') else ''})",
                "nearest_mtr_cn": match.get("station_zh", current_mtr.get("nearest_mtr_cn", "")),
                "nearest_mtr_en": match.get("station_en", current_mtr.get("nearest_mtr_en", "")),
                "nearest_mtr_lines": "/".join(match.get("lines", [])) if isinstance(match.get("lines"), list) else match.get("lines", ""),
                "nearest_mtr_lat": match.get("station_lat", current_mtr.get("nearest_mtr_lat")),
                "nearest_mtr_lng": match.get("station_lng", current_mtr.get("nearest_mtr_lng")),
                "dist_straight_m": match.get("straight_distance", current_mtr.get("dist_straight_m")),
                "dist_walk_m": w_dist,
                "walk_time_min": w_dur,
                "route_geometry": match.get("route_geometry")
            }
            updated += 1
        elif p_lat and p_lng:
            # 2. 在线计算真实人行道路线
            closest_st = min(MTR_STATIONS, key=lambda s: dist_m(p_lat, p_lng, s["lat"], s["lng"]))
            straight_m = round(dist_m(p_lat, p_lng, closest_st["lat"], closest_st["lng"]))
            route = ors_walk(p_lat, p_lng, closest_st["lat"], closest_st["lng"])
            if not route:
                route = osrm_walk(p_lat, p_lng, closest_st["lat"], closest_st["lng"])
            time.sleep(0.5)
            
            if route:
                walk_m = route["distance"]
                dur_raw = route["duration"] / 60.0
                speed_kmh = (walk_m / 1000.0) / (dur_raw / 60.0) if dur_raw > 0 else 0
                if 2.5 <= speed_kmh <= 6.5:
                    walk_min = round(dur_raw, 1)
                else:
                    walk_min = round(walk_m / 75.0, 1)
                route_geo = route["geometry"]
            else:
                walk_m = round(straight_m * 1.3)
                walk_min = round(walk_m / 75.0, 1)
                route_geo = None
            
            p["nearest_mtr"] = {
                "address": "",
                "nearest_mtr_cn": closest_st["name_zh"],
                "nearest_mtr_en": closest_st["name_en"],
                "nearest_mtr_lines": "/".join(closest_st["lines"]),
                "nearest_mtr_lat": closest_st["lat"],
                "nearest_mtr_lng": closest_st["lng"],
                "dist_straight_m": straight_m,
                "dist_walk_m": walk_m,
                "walk_time_min": walk_min,
                "route_geometry": route_geo
            }
            calculated_on_fly += 1
            updated += 1
            print(f"   ⚡ 在线测算补充: {p_name} → {closest_st['name_zh']} ({walk_m}m, {walk_min}min)")

    print(f"\n3️⃣ 保存更新后的 {COORDS_PATH}...")
    with open(COORDS_PATH, "w", encoding="utf-8") as f:
        json.dump(sandbox_projects, f, ensure_ascii=False, indent=2)
    
    total_with_geo = sum(1 for p in sandbox_projects if p.get("nearest_mtr", {}).get("route_geometry", {}).get("coordinates"))
    print(f"   ✅ 完成！共 {len(sandbox_projects)} 个楼盘，成功挂载真实路线数据 {total_with_geo} 个 (其中在线补充 {calculated_on_fly} 个)")

if __name__ == "__main__":
    main()
