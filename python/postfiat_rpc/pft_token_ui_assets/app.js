"use strict";

const EXPLORERS = {
  8453: { name: "Base", address: "https://base.blockscout.com/address/" },
  84532: { name: "Base Sepolia", address: "https://base-sepolia.blockscout.com/address/" },
};

const $ = (id) => document.getElementById(id);

function grouped(digits) {
  const [whole, fraction] = String(digits).split(".");
  const withCommas = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  return fraction ? `${withCommas}.${fraction}` : withCommas;
}

function addressLink(element, address, chainId) {
  const explorer = EXPLORERS[chainId];
  element.textContent = address;
  if (explorer && /^0x[0-9a-fA-F]{40}$/.test(address)) {
    element.href = explorer.address + address;
    element.title = `Open on Blockscout (${explorer.name})`;
  } else {
    element.removeAttribute("href");
  }
}

function render(state) {
  const explorer = EXPLORERS[state.chain_id];
  $("title").textContent = `${state.name} (${state.symbol})`;
  addressLink($("token"), state.token, state.chain_id);
  addressLink($("treasury"), state.treasury, state.chain_id);
  $("chain").textContent = explorer ? `${explorer.name} (${state.chain_id})` : String(state.chain_id);
  $("decimals").textContent = String(state.decimals);
  $("supply-pft").textContent = `${grouped(state.total_supply_pft)} ${state.symbol}`;
  $("supply-units").textContent = `${grouped(state.total_supply_units)} units`;
  $("balance-pft").textContent = `${grouped(state.treasury_balance_pft)} ${state.symbol}`;
  $("balance-units").textContent = `${grouped(state.treasury_balance_units)} units`;
  $("code-size").textContent = `${grouped(state.code_size_bytes)} bytes`;
  $("block").textContent = grouped(state.block_number);
  $("read-at").textContent = state.read_at;
  $("rpc").textContent = state.rpc_url;

  const verdict = $("whole-supply");
  const holds = state.treasury_holds_whole_supply === true;
  verdict.hidden = false;
  verdict.className = `verdict ${holds ? "verdict--ok" : "verdict--bad"}`;
  verdict.textContent = holds
    ? "The treasury holds the whole supply"
    : "The treasury does not hold the whole supply";
}

async function refresh() {
  const button = $("refresh");
  const status = $("status");
  button.disabled = true;
  status.className = "status";
  status.textContent = "Reading the token…";
  try {
    const response = await fetch("/api/state", { cache: "no-store" });
    const body = await response.json();
    if (!response.ok) {
      throw new Error(`${body.refused ? "Refused" : "Failed"}: ${body.error}`);
    }
    render(body);
    status.textContent = `Fetched ${body.fetched_at}`;
  } catch (error) {
    status.className = "status status--error";
    status.textContent = error.message;
  } finally {
    button.disabled = false;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  $("refresh").addEventListener("click", refresh);
  refresh();
});
