import re


def test_parser(line):
    print(f"Testando linha: {line}")
    pattern = r'Player "(?P<name>[^"]+)" \(id=[^ ]+ pos=<(?P<coords>[^>]+)>\)(?P<action_line>.+)'
    match = re.search(pattern, line)

    if not match:
        print("FALHA: Regex principal não casou")
        return

    player_name = match.group("name")
    coords_str = match.group("coords")
    action_line = match.group("action_line")

    print(f"Nome: {player_name}")
    print(f"Coords: {coords_str}")
    print(f"Ação: {action_line}")

    action_line_lower = action_line.lower()
    if "built" in action_line_lower:
        item_name = (
            action_line.split("built ")[1].split(" on")[0].split(" with")[0].strip()
        )
        print(f"ITEM CONSTRUÍDO: {item_name}")


# Linhas reais do log
lines = [
    '18:07:08 | Player "GuiBonaZza" (id=2FD5C5A53739AA25501401B4A4C46F0656A9E829 pos=<6980.8, 9880.2, 377.1>)Built base on Fence with Pickaxe',
    '18:17:29 | Player "GuiBonaZza" (id=2FD5C5A53739AA25501401B4A4C46F0656A9E829 pos=<6976.9, 9880.8, 377.1>)Built wall_gate on Gate with Pliers',
    '17:42:53 | Player "Jamaika227741" (id=2BA6AE4D44C492521B2F67E16FAF0B48D309D505 pos=<10308.6, 3613.5, 41.2>) placed Fence Kit<FenceKit>',
]

for l in lines:
    test_parser(l)
    print("-" * 20)
