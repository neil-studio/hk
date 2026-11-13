import json
import math
import os
import shutil

def point_line_distance(point, start, end):
    if start == end:
        return math.hypot(point[0] - start[0], point[1] - start[1])
    line_mag = (end[0] - start[0])**2 + (end[1] - start[1])**2
    if line_mag == 0:
        return math.hypot(point[0] - start[0], point[1] - start[1])
    u = ((point[0] - start[0]) * (end[0] - start[0]) + (point[1] - start[1]) * (end[1] - start[1])) / line_mag
    if u < 0.0:
        return math.hypot(point[0] - start[0], point[1] - start[1])
    elif u > 1.0:
        return math.hypot(point[0] - end[0], point[1] - end[1])
    ix = start[0] + u * (end[0] - start[0])
    iy = start[1] + u * (end[1] - start[1])
    return math.hypot(point[0] - ix, point[1] - iy)

def ramer_douglas_peucker(points, epsilon):
    if len(points) <= 2:
        return points
    dmax = 0.0
    index = 0
    end = len(points) - 1
    for i in range(1, end):
        d = point_line_distance(points[i], points[0], points[end])
        if d > dmax:
            index = i
            dmax = d
    if dmax > epsilon:
        rec_results1 = ramer_douglas_peucker(points[:index+1], epsilon)
        rec_results2 = ramer_douglas_peucker(points[index:], epsilon)
        return rec_results1[:-1] + rec_results2
    else:
        return [points[0], points[end]]

def simplify_ring(ring, epsilon):
    if len(ring) < 4:
        return ring
    is_closed = (ring[0] == ring[-1])
    pts = ring[:-1] if is_closed else ring
    simplified = ramer_douglas_peucker(pts, epsilon)
    if is_closed:
        simplified.append(simplified[0])
    if len(simplified) < 4:
        return ring
    return simplified

def round_coords(coords, precision=5):
    if isinstance(coords[0], (int, float)):
        return [round(coords[0], precision), round(coords[1], precision)]
    return [round_coords(c, precision) for c in coords]

def simplify_geom(geom, epsilon, precision=5):
    geom_type = geom.get('type')
    coords = geom.get('coordinates', [])
    if geom_type == 'Polygon':
        new_coords = [simplify_ring(r, epsilon) for r in coords]
        return {'type': geom_type, 'coordinates': round_coords(new_coords, precision)}
    elif geom_type == 'MultiPolygon':
        new_coords = [[simplify_ring(r, epsilon) for r in poly] for poly in coords]
        return {'type': geom_type, 'coordinates': round_coords(new_coords, precision)}
    return geom

def optimize_all():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 1. GeoJSON Optimization
    geo_src = os.path.join(base_dir, 'hong_kong_micro_districts.geojson')
    geo_bak = os.path.join(base_dir, 'hong_kong_micro_districts.geojson.bak')
    if not os.path.exists(geo_bak):
        shutil.copy2(geo_src, geo_bak)
        
    with open(geo_bak, 'r', encoding='utf-8') as f:
        geo_data = json.load(f)
        
    eps = 0.00005  # ~5米容差，平衡细腻轮廓与极小体积
    clean_features = []
    for feat in geo_data['features']:
        orig_props = feat.get('properties', {})
        clean_props = {
            'id': feat.get('id') or orig_props.get('id'),
            'micro_district': orig_props.get('micro_district'),
            'micro_district_en': orig_props.get('micro_district_en'),
            'main_area': orig_props.get('main_area'),
            'color': orig_props.get('color', '#3b82f6')
        }
        clean_features.append({
            'type': 'Feature',
            'id': feat.get('id'),
            'properties': clean_props,
            'geometry': simplify_geom(feat['geometry'], eps, precision=5)
        })
        
    compact_geo = {
        'type': 'FeatureCollection',
        'name': geo_data.get('name', 'HongKong_Micro_Districts'),
        'features': clean_features
    }
    with open(geo_src, 'w', encoding='utf-8') as f:
        json.dump(compact_geo, f, separators=(',', ':'), ensure_ascii=False)
        
    print(f"✅ hong_kong_micro_districts.geojson: {os.path.getsize(geo_src)/1024:.1f} KB (原始: {os.path.getsize(geo_bak)/1024/1024:.2f} MB)")

    # 2. Project Coords Minification
    coords_path = os.path.join(base_dir, 'hk_project_coords.json')
    if os.path.exists(coords_path):
        with open(coords_path, 'r', encoding='utf-8') as f:
            c_data = json.load(f)
        with open(coords_path, 'w', encoding='utf-8') as f:
            json.dump(c_data, f, separators=(',', ':'), ensure_ascii=False)
        print(f"✅ hk_project_coords.json: {os.path.getsize(coords_path)/1024:.1f} KB")

    # 3. Landmarks Minification
    for fname in ['hk_landmarks.json', 'hk_mtr_stations.json']:
        fpath = os.path.join(base_dir, fname)
        if os.path.exists(fpath):
            with open(fpath, 'r', encoding='utf-8') as f:
                d = json.load(f)
            with open(fpath, 'w', encoding='utf-8') as f:
                json.dump(d, f, separators=(',', ':'), ensure_ascii=False)
            print(f"✅ {fname}: {os.path.getsize(fpath)/1024:.1f} KB")

if __name__ == '__main__':
    optimize_all()
