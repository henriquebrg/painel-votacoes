export function formatarData(iso) {
  const partes = Object.fromEntries(
    new Intl.DateTimeFormat("pt-BR", {
      timeZone: "America/Sao_Paulo",
      day: "2-digit", month: "2-digit", year: "numeric",
      hour: "2-digit", minute: "2-digit", hourCycle: "h23"
    }).formatToParts(new Date(iso)).map((p) => [p.type, p.value])
  );
  return `${partes.day}/${partes.month}/${partes.year} ${partes.hour}:${partes.minute}`;
}

export function textoRodape(meta) {
  return `Fonte: ${meta.fonte} · Atualizado em ${formatarData(meta.atualizado_em)}`;
}

export function rodape(meta) {
  const el = document.createElement("footer");
  el.className = "rodape-fonte";
  el.textContent = textoRodape(meta);
  return el;
}
