// ============================================================================
// BIGODEBOT - SISTEMA DE ENTREGA DE ITENS DAYZ
// ============================================================================
// ATENÇÃO: Este é um arquivo ENFORCE SCRIPT (linguagem do DayZ), NÃO é C!
//
// Se você está vendo erros na IDE como:
//   - "Use of undeclared identifier 'GetGame'"
//   - "Unknown type name 'class'"
//   - "Use of undeclared identifier 'Weather'"
//
// IGNORE ESSES ERROS! Eles são falsos positivos.
// O código está correto e funcionará no servidor DayZ.
//
// Para mais informações, leia: INIT_README.md
// ============================================================================

void main() {
  // INIT WEATHER BEFORE ECONOMY INIT------------------------
  Weather weather = g_Game.GetWeather();

  weather.MissionWeather(
      false); // false = use weather controller from Weather.c

  weather.GetOvercast().Set(Math.RandomFloatInclusive(0.4, 0.6), 1, 0);
  weather.GetRain().Set(0, 0, 1);
  weather.GetFog().Set(Math.RandomFloatInclusive(0.05, 0.1), 1, 0);

  // INIT ECONOMY--------------------------------------
  Hive ce = CreateHive();
  if (ce)
    ce.InitOffline();

  // DATE RESET AFTER ECONOMY INIT-------------------------
  int year, month, day, hour, minute;
  int reset_month = 9, reset_day = 20;
  GetGame().GetWorld().GetDate(year, month, day, hour, minute);

  if ((month == reset_month) && (day < reset_day)) {
    GetGame().GetWorld().SetDate(year, reset_month, reset_day, hour, minute);
  } else {
    if ((month == reset_month + 1) && (day > reset_day)) {
      GetGame().GetWorld().SetDate(year, reset_month, reset_day, hour, minute);
    } else {
      if ((month < reset_month) || (month > reset_month + 1)) {
        GetGame().GetWorld().SetDate(year, reset_month, reset_day, hour,
                                     minute);
      }
    }
  }
}

// --- ESTRUTURA PARA DELETAR OBJETOS ---
class DeletionItem {
  string coords; // Formato "X Y Z"
}

class DeletionData {
  ref array<ref DeletionItem> items;
  void DeletionData() { items = new array<ref DeletionItem>; }
}

// --- ESTRUTURA PARA DISPONIBILIDADE ---
class AvailableTruckItem { string coords; }

class AvailableTruckData {
  ref array<ref AvailableTruckItem> items;
  void AvailableTruckData() { items = new array<ref AvailableTruckItem>; }
}
// ---------------------------------------

class CustomMission : MissionServer {
  override void OnInit() {
    super.OnInit();

    // Loop de spawns (Bot -> Servidor)
    GetGame()
        .GetCallQueue(CALL_CATEGORY_GAMEPLAY)
        .CallLater(CheckSpawns, 60000, true);

    // Loop de deleções (Bot -> Servidor)
    GetGame()
        .GetCallQueue(CALL_CATEGORY_GAMEPLAY)
        .CallLater(CheckDeletions, 30000, true);

    // Loop de Scanner de Caminhões (Servidor -> Bot) - A cada 10 min
    GetGame()
        .GetCallQueue(CALL_CATEGORY_GAMEPLAY)
        .CallLater(CheckAvailableTrucks, 600000, true);

    Print("[BigodeBot] Sistemas de Kit Truck Ativos (Spawn/Delete/Scanner).");
  }

  void CheckAvailableTrucks() {
    array<vector> spawns = {
        "2906 0 9736",   "1577 0 10434",  "4986 0 12949",  "5960 0 10146",
        "8667 0 13278",  "5664 0 13129",  "4832 0 10236",  "5276 0 10581",
        "1045 0 9971",   "5227 0 11521",  "3789 0 13001",  "1798 0 9127",
        "2009 0 10077",  "7735 0 14834",  "8857 0 11649",  "4131 0 13122",
        "2276 0 15255",  "1522 0 14049",  "3251 0 13731",  "5770 0 15185",
        "4406 0 13568",  "7748 0 5119",   "3575 0 6990",   "7791 0 6910",
        "7076 0 2689",   "3633 0 3692",   "4429 0 8215",   "2220 0 5200",
        "560 0 5410",    "4637 0 9505",   "8405 0 6596",   "6944 0 7693",
        "1364 0 4114",   "8409 0 4441",   "2206 0 3372",   "3012 0 6762",
        "2041 0 12167",  "7299 0 3309",   "10554 0 14322", "6265 0 3786",
        "10362 0 7419",  "9004 0 5989",   "2733 0 5996",   "5339 0 8617",
        "5678 0 2970",   "10224 0 1893",  "13058 0 7050",  "11327 0 12564",
        "7414 0 2902",   "9372 0 2017",   "12373 0 14194", "12766 0 9737",
        "12291 0 9180",  "9914 0 6694",   "9851 0 8710",   "11758 0 6440",
        "12659 0 8792",  "7043 0 2621",   "12046 0 5117",  "10289 0 14176",
        "2253 0 10861",  "4193 0 8920",   "6324 0 7708",   "5281 0 5511",
        "8214 0 9051",   "981 0 7679",    "9186 0 8092",   "4045 0 11620",
        "4957 0 13034",  "7711 0 3541",   "5258 0 9789",   "4812 0 10559",
        "5081 0 12738",  "289 0 6591",    "2311 0 5205",   "3040 0 12342",
        "3115 0 9212",   "1927 0 8118",   "11119 0 11950", "12252 0 10592",
        "10268 0 9484",  "9788 0 12659",  "3588 0 2191",   "12739 0 15065",
        "4962 0 2423",   "9684 0 8900",   "11443 0 7523",  "8076 0 3367",
        "12658 0 14744", "13471 0 13067", "11714 0 14243", "12304 0 14322",
        "11951 0 12505", "11617 0 7294",  "9901 0 5467",   "10257 0 3617"};

    AvailableTruckData data = new AvailableTruckData;
    foreach (vector spawnPos : spawns) {
      array<Object> objects = new array<Object>;
      GetGame().GetObjectsAtPosition3D(spawnPos, 5.0, objects, null);
      foreach (Object obj : objects) {
        if (obj.IsVehicle()) {
          AvailableTruckItem item = new AvailableTruckItem;
          item.coords = spawnPos.ToString();
          data.items.Insert(item);
          break;
        }
      }
    }

    if (data.items.Count() > 0) {
      JsonFileLoader<AvailableTruckData>.JsonSaveFile(
          "$profile:truck_availability.json", data);
      Print("[BigodeBot] Scanner: Encontrados " + data.items.Count() +
            " caminhoes nos spawns.");
    }
  }

  void CheckDeletions() {
    string filepath = "$profile:deletions.json";
    if (FileExist(filepath)) {
      DeletionData data = new DeletionData;
      string error;

      if (JsonFileLoader<DeletionData>.LoadFile(filepath, data, error)) {
        if (data && data.items) {
          foreach (DeletionItem item : data.items) {
            vector pos = item.coords.ToVector();
            array<Object> objects = new array<Object>;
            GetGame().GetObjectsAtPosition3D(pos, 2.0, objects, null);

            foreach (Object obj : objects) {
              if (obj.IsVehicle()) {
                Print("[BigodeBot] Deletando veiculo solicitado em " +
                      item.coords);
                GetGame().ObjectDelete(obj);
              }
            }
          }
        }
        DeleteFile(filepath);
        Print("[BigodeBot] Delecoes concluidas.");
      }
    }
  }

  void CheckSpawns() {
    // Caminho do arquivo que o BOT vai enviar via FTP
    // Nota: O bot deve enviar para a pasta que corresponde ao $profile (ex: SC
    // ou config)
    string filepath = "$profile:spawns.json";

    if (FileExist(filepath)) {
      Print("[BigodeBot] Arquivo de spawns encontrado. Processando...");

      SpawnData data = new SpawnData;
      string error;

      if (JsonFileLoader<SpawnData>.LoadFile(filepath, data, error)) {
        if (data && data.items) {
          foreach (SpawnItem item : data.items) {
            if (!item)
              continue;

            vector pos = item.coords.ToVector();
            // Se o usuario mandou so X Z (2D), ajusta Y (altura)
            if (pos[1] == 0) {
              pos[1] = GetGame().SurfaceY(pos[0], pos[2]);
            }

            EntityAI obj =
                EntityAI.Cast(GetGame().CreateObject(item.name, pos));
            if (obj) {
              Print("[BigodeBot] Item entregue: " + item.name + " em " +
                    item.coords);
            } else {
              Print("[BigodeBot] FALHA ao entregar: " + item.name);
            }
          }
        }

        // Limpa o arquivo para não spawnar de novo
        // Opção 1: Deletar (DeleteFile(filepath))
        // Opção 2: Limpar conteúdo
        DeleteFile(filepath);
        Print("[BigodeBot] Entregas concluidas e arquivo limpo.");
      } else {
        Print("[BigodeBot] Erro ao ler JSON: " + error);
      }
    }
  }
}
