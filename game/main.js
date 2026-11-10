// Exemplo sintético apenas para validação da interface.
const size = 96;
const vegetationBefore = 58;
const vegetationAfter = 69;
const referenceDeltaPP = vegetationAfter - vegetationBefore; // +11 pontos percentuais
const seeded = (i) => ((i * 37 + 13) % size);
function draw(id, count) {
  const host = document.getElementById(id);
  const greenIndices = new Set(Array.from({ length: count }, (_, i) => seeded(i)));
  for (let i = 0; i < size; i++) {
    const tile = document.createElement('span');
    tile.className = `tile ${greenIndices.has(i) ? 'green' : 'gray'}`;
    host.appendChild(tile);
  }
}
draw('before', vegetationBefore);
draw('after', vegetationAfter);
const guess = document.getElementById('guess');
const value = document.getElementById('value');
const result = document.getElementById('result');
guess.addEventListener('input', () => {value.textContent = `${Number(guess.value)>0?'+':''}${guess.value} p.p.`;result.textContent = '';});
document.getElementById('check').addEventListener('click', () => {
  const answer = Number(guess.value);
  const error = Math.abs(answer - referenceDeltaPP);
  const points = Math.max(0, Math.round(1000 - 30 * error));
  result.textContent = `Referência sintética: +${referenceDeltaPP} p.p. · Erro: ${error} p.p. · Pontuação: ${points}.`;
});
