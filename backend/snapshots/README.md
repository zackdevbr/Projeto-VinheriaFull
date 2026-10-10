# Fotos do banco local

Cópias do `vinheria.db` guardadas de propósito no repositório. O banco em uso
(`backend/vinheria.db`) continua fora do Git, e os backups automáticos ficam
em `~/SmartSolutions/backups/` (ver `BACKUP_DIR` no `.env`).

| Arquivo | O que tem | Para que serve |
|---|---|---|
| `vinheria-pre-task4.db` | Estado de 08/10/2026, antes da Task 4: `vinheria001` (Vinheria Paulista, São Paulo) e `vinheria002` (Vinheria Mineira, Minas Gerais) com a faixa padrão e nenhum alerta. | Começo limpo para a demo, sem os alertas dos testes. |

## Como usar

Com o backend **parado**, a partir de `backend/`:

```bash
.venv/Scripts/python -m app.tools.restore_backup snapshots/vinheria-pre-task4.db
```

O comando valida o arquivo e guarda o banco atual como
`vinheria.db.antes-da-restauracao-<data>` antes de substituir.

Depois de restaurar, as vinherias precisam existir no FIWARE com o atributo
`configured`; se não existirem, recadastre-as (`DELETE` e `POST /api/devices`
com o mesmo nome e cidade).

Não coloque aqui bancos com dados reais de clientes.
