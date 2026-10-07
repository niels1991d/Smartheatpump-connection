# smartheatpump-connection

Lees en stuur je warmtepomp aan die je nu met de **Smart Heatpump**-app (Tuya) bedient,
zonder de app: via je eigen netwerk (lokaal) of via de Tuya-cloud.

## Installeren

```bash
pip install -e .
```

## 1. Gegevens van je warmtepomp ophalen (eenmalig)

Je hebt een **device ID** en een **local key** nodig. Die haal je zo op:

1. Maak een gratis account aan op <https://iot.tuya.com> en maak een *Cloud Project* aan
   (datacenter: **Central Europe**).
2. Ga in het project naar *Devices → Link App Account* en scan de QR-code met de
   Smart Heatpump-app (of Smart Life / Tuya Smart). Je warmtepomp verschijnt in de lijst.
3. Voer de wizard uit en vul de API key/secret van je project in:
   ```bash
   python -m tinytuya wizard
   ```
   Daarna staan `id`, `key` (= local key) en het IP-adres in `devices.json`.

Zoek eventueel het IP-adres op je netwerk met `smartheatpump scan`.

## 2. Configureren

```bash
cp config.example.json config.json   # en vul in
```

Voor **lokaal** zijn `device_id`, `ip` en `local_key` genoeg.
Voor **cloud** (werkt overal, ook buitenshuis) vul je `device_id`, `api_key`, `api_secret` in.
Alles kan ook via omgevingsvariabelen: `SHP_DEVICE_ID`, `SHP_IP`, `SHP_LOCAL_KEY`,
`SHP_API_KEY`, `SHP_API_SECRET`, `SHP_API_REGION`. `config.json` wordt niet in git opgenomen.

## 3. Gebruiken

```bash
smartheatpump status          # aan/uit, watertemperatuur, doeltemperatuur, modus
smartheatpump on | off
smartheatpump set-temp 28
smartheatpump set-mode heat   # waarde verschilt per model
smartheatpump log --interval 60 --file warmtepomp.csv
smartheatpump dps             # alle ruwe datapoints
smartheatpump --via cloud status
```

Of vanuit Python:

```python
from smartheatpump import HeatPump, load_config

pump = HeatPump(load_config())
print(pump.status().as_dict())
pump.set_target_temp(28)
```

## Datapoints aanpassen

Elk warmtepompmodel gebruikt eigen datapoint-nummers (DP's). De standaard is
`power=1, target_temp=2, current_temp=3, mode=4, fault=15`. Klopt de status niet?

1. Run `smartheatpump dps`, verander iets in de app en run het opnieuw. Kijk welk nummer
   meeverandert.
2. Pas `dp_map` in `config.json` aan.
3. Geeft je pomp temperaturen ×10 terug (bijv. `285` voor 28,5 °C)? Zet dan `"temp_scale": 10`.

Via de cloud heten de DP's codes (bijv. `"switch"`, `"temp_set"`). Gebruik die namen dan in `dp_map`.

## Tests

```bash
pip install pytest && pytest
```
