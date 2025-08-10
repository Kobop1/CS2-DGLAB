import winreg
from pathlib import Path

def find_cs2_install_path() -> str:
    """查找CS2安装路径"""
    try:
        # 从注册表获取Steam安装路径
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Software\Valve\Steam', 0, winreg.KEY_READ) as key:
            steam_path, _ = winreg.QueryValueEx(key, 'SteamPath')
            steam_path = Path(steam_path)
    except Exception as e:
        raise RuntimeError(f"获取Steam路径失败: {e}")

    # 读取库文件夹配置
    lib_path = steam_path / 'steamapps' / 'libraryfolders.vdf'
    if not lib_path.exists():
        raise FileNotFoundError("Steam库配置文件不存在")

    last_path = None
    found = False
    with open(lib_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip('\n').strip('\t')
            if line.startswith('"path"'):
                _, path_val = line.split('\t\t')
                last_path = Path(path_val.strip('"').encode().decode('unicode_escape'))
            elif '"730"' in line:  # 730是CS2的AppID
                found = True
                break

    if not found or not last_path:
        raise FileNotFoundError("未找到CS2安装路径")

    # 验证CS2路径
    cs2_paths = [
        last_path / 'steamapps' / 'common' / 'Counter-Strike Global Offensive',
        last_path / 'game' / 'csgo'
    ]
    for path in cs2_paths:
        if path.exists():
            return str(path)
    
    raise FileNotFoundError("CS2安装路径验证失败")

def setup_cs2_gamestate_cfg(cs2_path: str) -> bool:
    """配置CS2游戏状态集成文件"""
    cfg_content = """"CS2&DGLAB"
{
 "uri" "http://127.0.0.1:3000"
 "timeout" "0.1"
 "buffer"  "0.1"
 "throttle" "0.5"
 "heartbeat" "1.0"
 "auth"
 {
   "token" "MYTOKENHERE"
 }
 "data"
 {
   "provider"            "1"
   "map"                 "1"
   "round"               "1"
   "player_id"           "1"
   "player_state"        "1"
 }
}
"""
    try:
        # 可能的CFG路径
        cfg_paths = [
            Path(cs2_path) / 'csgo' / 'cfg',
            Path(cs2_path) / 'game' / 'csgo' / 'cfg'
        ]
        for cfg_dir in cfg_paths:
            if cfg_dir.exists():
                cfg_file = cfg_dir / 'gamestate_integration_nodecs2.cfg'
                with open(cfg_file, 'w', encoding='utf-8') as f:
                    f.write(cfg_content)
                return True
        return False
    except Exception as e:
        raise RuntimeError(f"配置CS2 CFG文件失败: {e}")
    