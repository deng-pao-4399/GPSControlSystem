import serial
import time
from datetime import datetime, timedelta
import math

# 尝试导入坐标转换库
try:
    import pyproj
    print("成功导入pyproj库")
    HAS_PYPROJ = True
except ImportError:
    print("尝试安装pyproj库...")
    try:
        import subprocess
        subprocess.check_call(["pip", "install", "pyproj"])
        import pyproj
        print("成功安装并导入pyproj库")
        HAS_PYPROJ = True
    except Exception as e:
        print(f"安装pyproj失败: {e}")
        HAS_PYPROJ = False

# 配置串口参数
SERIAL_PORT = '/dev/ttyS3'
BAUD_RATE = 9600

# 打开串口
try:
    ser = serial.Serial(
        port=SERIAL_PORT,
        baudrate=BAUD_RATE,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        timeout=1
    )
    print(f"成功打开串口 {SERIAL_PORT}")
except Exception as e:
    print(f"打开串口失败: {e}")
    print("请检查：")
    print("1. GPS模块是否正确连接到ttyS3串口")
    print("2. 串口是否被其他程序占用")
    print("3. 是否有串口访问权限（可尝试：sudo chmod 666 /dev/ttyS3）")
    exit(1)

def parse_nmea_coordinate(coord_str, direction):
    """解析NMEA格式的坐标"""
    try:
        if not coord_str or len(coord_str) < 7:
            return 0.0
            
        if direction in ['N', 'S']:
            # 纬度格式：ddmm.mmmm
            deg = float(coord_str[:2])
            minutes = float(coord_str[2:])
        else:
            # 经度格式：dddmm.mmmm
            deg = float(coord_str[:3])
            minutes = float(coord_str[3:])
            
        decimal_degrees = deg + minutes / 60.0
        
        if direction in ['S', 'W']:
            decimal_degrees = -decimal_degrees
            
        return decimal_degrees
    except Exception as e:
        return 0.0

def wgs84_to_gcj02(lon, lat):
    """WGS84转GCJ02（火星坐标）"""
    # 转换参数
    a = 6378245.0
    ee = 0.00669342162296594323
    pi = 3.1415926535897932384626
    
    def transform_lat(x, y):
        ret = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * math.sqrt(abs(x))
        ret += (20.0 * math.sin(6.0 * x * pi) + 20.0 * math.sin(2.0 * x * pi)) * 2.0 / 3.0
        ret += (20.0 * math.sin(y * pi) + 40.0 * math.sin(y / 3.0 * pi)) * 2.0 / 3.0
        ret += (160.0 * math.sin(y / 12.0 * pi) + 320 * math.sin(y * pi / 30.0)) * 2.0 / 3.0
        return ret
    
    def transform_lon(x, y):
        ret = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * math.sqrt(abs(x))
        ret += (20.0 * math.sin(6.0 * x * pi) + 20.0 * math.sin(2.0 * x * pi)) * 2.0 / 3.0
        ret += (20.0 * math.sin(x * pi) + 40.0 * math.sin(x / 3.0 * pi)) * 2.0 / 3.0
        ret += (150.0 * math.sin(x / 12.0 * pi) + 300.0 * math.sin(x / 30.0 * pi)) * 2.0 / 3.0
        return ret
    
    dlat = transform_lat(lon - 105.0, lat - 35.0)
    dlon = transform_lon(lon - 105.0, lat - 35.0)
    radlat = lat / 180.0 * pi
    magic = math.sin(radlat)
    magic = 1 - ee * magic * magic
    sqrtmagic = math.sqrt(magic)
    dlat = (dlat * 180.0) / ((a * (1 - ee)) / (magic * sqrtmagic) * pi)
    dlon = (dlon * 180.0) / (a / sqrtmagic * math.cos(radlat) * pi)
    
    mglat = lat + dlat
    mglon = lon + dlon
    
    return mglon, mglat

def gcj02_to_bd09(lon, lat):
    """GCJ02转BD09（百度坐标）"""
    pi = 3.1415926535897932384626
    z = math.sqrt(lon * lon + lat * lat) + 0.00002 * math.sin(lat * pi)
    theta = math.atan2(lat, lon) + 0.000003 * math.cos(lon * pi)
    bd_lon = z * math.cos(theta) + 0.0065
    bd_lat = z * math.sin(theta) + 0.006
    return bd_lon, bd_lat

def wgs84_to_bd09(lon, lat):
    """WGS84转BD09（通过GCJ02中转）"""
    gcj_lon, gcj_lat = wgs84_to_gcj02(lon, lat)
    bd_lon, bd_lat = gcj02_to_bd09(gcj_lon, gcj_lat)
    return bd_lon, bd_lat

def convert_with_pyproj(lon, lat):
    """使用pyproj进行坐标转换"""
    try:
        # WGS84坐标系
        wgs84 = pyproj.CRS('EPSG:4326')
        
        # GCJ02（使用近似转换，pyproj没有内置GCJ02）
        gcj_lon, gcj_lat = wgs84_to_gcj02(lon, lat)
        
        # BD09（百度坐标）
        bd_lon, bd_lat = gcj02_to_bd09(gcj_lon, gcj_lat)
        
        return {
            'wgs84': (lon, lat),
            'gcj02': (gcj_lon, gcj_lat),
            'bd09': (bd_lon, bd_lat)
        }
    except Exception as e:
        print(f"pyproj转换错误: {e}")
        return None

def parse_gngga_line(line):
    """解析$GNGGA行数据"""
    print("=" * 80)
    print(f"原始GNGGA数据: {line.strip()}")
    
    line = line.strip()
    parts = line.split(',')
    
    if len(parts) < 15:
        print("数据格式错误或数据不完整")
        return None
    
    # 提取字段
    sentence_id = parts[0]
    utc_time = parts[1]
    latitude = parts[2]
    lat_direction = parts[3]
    longitude = parts[4]
    lon_direction = parts[5]
    fix_quality = parts[6]
    satellites = parts[7]
    hdop = parts[8]
    altitude = parts[9]
    altitude_unit = parts[10]
    
    print("\n=== GNGGA字段解析 ===")
    print(f"1. 语句ID: {sentence_id}")
    print(f"2. UTC时间: {utc_time}")
    print(f"3. 纬度: {latitude} {lat_direction}")
    print(f"4. 纬度方向: {lat_direction}")
    print(f"5. 经度: {longitude} {lon_direction}")
    print(f"6. 经度方向: {lon_direction}")
    print(f"7. 定位质量: {fix_quality}", end="")
    
    # 定位质量描述
    fix_dict = {
        '0': '无效定位',
        '1': 'GPS单点定位',
        '2': '差分GPS定位',
        '3': 'PPS定位',
        '4': 'RTK固定解',
        '5': 'RTK浮点解'
    }
    
    if fix_quality in fix_dict:
        print(f" ({fix_dict[fix_quality]})")
    else:
        print()
    
    print(f"8. 可用卫星数: {satellites}")
    print(f"9. 水平精度因子(HDOP): {hdop}")
    
    if altitude and altitude != '':
        print(f"10. 海拔高度: {altitude} {altitude_unit}")
    
    # 解析时间
    if utc_time and len(utc_time) >= 6:
        try:
            hour = int(utc_time[0:2])
            minute = int(utc_time[2:4])
            second = int(float(utc_time[4:]))
            
            today = datetime.utcnow().date()
            utc_datetime = datetime(
                today.year, today.month, today.day,
                hour, minute, second
            )
            
            beijing_datetime = utc_datetime + timedelta(hours=8)
            
            print("\n=== 时间信息 ===")
            print(f"UTC时间: {utc_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"北京时间: {beijing_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
        except Exception as e:
            print(f"\n时间解析错误: {e}")
    
    # 解析坐标
    if (latitude and longitude and 
        latitude != '' and longitude != '' and
        lat_direction in ['N', 'S'] and 
        lon_direction in ['E', 'W']):
        try:
            wgs84_lat = parse_nmea_coordinate(latitude, lat_direction)
            wgs84_lon = parse_nmea_coordinate(longitude, lon_direction)
            
            print("\n=== 坐标信息 ===")
            print(f"WGS84坐标: ")
            print(f"  纬度: {wgs84_lat:.8f}° ({lat_direction})")
            print(f"  经度: {wgs84_lon:.8f}° ({lon_direction})")
            
            # 度分秒格式
            lat_deg = int(abs(wgs84_lat))
            lat_min = (abs(wgs84_lat) - lat_deg) * 60
            lat_sec = (lat_min - int(lat_min)) * 60
            lat_dir = '北纬' if wgs84_lat >= 0 else '南纬'
            print(f"  纬度(度分秒): {lat_deg}°{int(lat_min)}'{lat_sec:.2f}\" {lat_dir}")
            
            lon_deg = int(abs(wgs84_lon))
            lon_min = (abs(wgs84_lon) - lon_deg) * 60
            lon_sec = (lon_min - int(lon_min)) * 60
            lon_dir = '东经' if wgs84_lon >= 0 else '西经'
            print(f"  经度(度分秒): {lon_deg}°{int(lon_min)}'{lon_sec:.2f}\" {lon_dir}")
            
            # 坐标转换
            if fix_quality != '0' and fix_quality != '':
                if HAS_PYPROJ:
                    coords = convert_with_pyproj(wgs84_lon, wgs84_lat)
                else:
                    # 使用本地函数转换
                    gcj_lon, gcj_lat = wgs84_to_gcj02(wgs84_lon, wgs84_lat)
                    bd_lon, bd_lat = gcj02_to_bd09(gcj_lon, gcj_lat)
                    coords = {
                        'wgs84': (wgs84_lon, wgs84_lat),
                        'gcj02': (gcj_lon, gcj_lat),
                        'bd09': (bd_lon, bd_lat)
                    }
                
                if coords:
                    print(f"\nGCJ02坐标(火星坐标/国测局坐标): ")
                    print(f"  纬度: {coords['gcj02'][1]:.8f}°")
                    print(f"  经度: {coords['gcj02'][0]:.8f}°")
                    
                    print(f"\nBD09坐标(百度坐标): ")
                    print(f"  纬度: {coords['bd09'][1]:.8f}°")
                    print(f"  经度: {coords['bd09'][0]:.8f}°")
                    
                    # 地图链接
                    baidu_url = f"https://api.map.baidu.com/marker?location={coords['bd09'][1]},{coords['bd09'][0]}&title=当前位置&output=html"
                    print(f"\n百度地图链接: {baidu_url}")
                    
                    amap_url = f"https://uri.amap.com/marker?position={coords['gcj02'][0]},{coords['gcj02'][1]}&name=当前位置"
                    print(f"高德地图链接: {amap_url}")
                    
                    # Google地图链接（使用WGS84坐标）
                    google_url = f"https://www.google.com/maps?q={wgs84_lat},{wgs84_lon}"
                    print(f"Google地图链接: {google_url}")
            
        except Exception as e:
            print(f"坐标解析错误: {e}")
    
    print("\n=== 定位状态 ===")
    if fix_quality == '0' or fix_quality == '':
        print("状态: 无效定位或无定位")
    elif satellites and satellites != '':
        sat_count = int(satellites) if satellites.isdigit() else 0
        if sat_count >= 6:
            print(f"状态: 优秀定位 (使用{sat_count}颗卫星)")
        elif sat_count >= 4:
            print(f"状态: 良好定位 (使用{sat_count}颗卫星)")
        else:
            print(f"状态: 定位较弱 (使用{sat_count}颗卫星)")
    else:
        print("状态: 定位数据不完整")
    
    print("=" * 80 + "\n")
    
    return {
        'fix_quality': fix_quality,
        'satellites': satellites
    }

# 主循环
print("开始接收GPS数据，按Ctrl+C退出...")
print("正在等待GPS定位...")
print("注意：首次定位可能需要几分钟（冷启动）\n")

try:
    while True:
        try:
            line = ser.readline().decode('ascii', errors='ignore')
            
            if line:
                if line.startswith('$GNGGA'):
                    parse_gngga_line(line)
                # 可选：显示其他NMEA语句用于调试
                elif line.startswith('$GP'):
                    print(f"GPS: {line.strip()}")
                elif line.startswith('$GN'):
                    print(f"GNSS: {line.strip()}")
                
        except UnicodeDecodeError:
            continue
        except Exception as e:
            print(f"读取错误: {e}")
            time.sleep(1)
            
except KeyboardInterrupt:
    print("\n\n程序被用户中断")
except Exception as e:
    print(f"\n程序运行错误: {e}")
finally:
    if 'ser' in locals() and ser.is_open:
        ser.close()
        print("串口已关闭")