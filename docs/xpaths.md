# XPath and Regex Reference

The selectors below are written against the location card shown in the assessment screenshot.

## 1) `locationName` (example value: `San Jacinto`)
Primary XPath:
```xpath
(//div[contains(@class,'location') and .//a[contains(@href,'/locations/')]])[1]//*[self::h2 or self::h3 or self::a][contains(normalize-space(.),'San Jacinto')]
```
Alternative generic XPath:
```xpath
(//div[contains(@class,'location')])[1]//*[self::h2 or self::h3 or self::a][1]
```

## 2) `hours` (example value: `Open until 3:00 PM`)
Primary XPath:
```xpath
(//div[contains(@class,'location')])[1]//*[contains(normalize-space(.),'Open until')]
```

## 3) `phoneNumber` (example value: `214-220-3911`)
Primary XPath:
```xpath
(//div[contains(@class,'location')])[1]//a[starts-with(@href,'tel:')]
```

## 4) `distance` (example value: `0.7 mi`)
Primary XPath:
```xpath
(//div[contains(@class,'location')])[1]//*[contains(normalize-space(.),' mi')]
```

## 5) Latitude and Longitude from `href`
Use XPath to capture the map URL/href that contains coordinates.

Primary XPath to href attribute:
```xpath
(//div[contains(@class,'location')])[1]//a[contains(@href,'maps') or contains(@href,'google')]/@href
```

If coordinates are in query format `q=lat,long`:
- Latitude regex:
```regex
(?:\?|&)q=(-?\d{1,2}\.\d+),(-?\d{1,3}\.\d+)
```
  - capture group 1 = latitude
- Longitude regex:
```regex
(?:\?|&)q=(-?\d{1,2}\.\d+),(-?\d{1,3}\.\d+)
```
  - capture group 2 = longitude

If coordinates are in path format `@lat,long`:
- Latitude regex:
```regex
@(-?\d{1,2}\.\d+),(-?\d{1,3}\.\d+)
```
  - capture group 1 = latitude
- Longitude regex:
```regex
@(-?\d{1,2}\.\d+),(-?\d{1,3}\.\d+)
```
  - capture group 2 = longitude

## Minimal generic coordinate patterns
- Latitude: `(-?\d{1,2}\.\d+)`
- Longitude: `(-?\d{1,3}\.\d+)`
