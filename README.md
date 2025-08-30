# Tiny Redis-like TCP Cache

Простейший TCP-кэш в стиле Redis: поддерживает команды `SET`, `GET`, TTL через `EX`.

## Протокол
Команды передаются в текстовом виде, одна команда в строке (`\n`).

- `SET key value [EX seconds]` → `OK` | `ERR ...`
- `GET key` → `<value>` | `(nil)` | `ERR ...`

