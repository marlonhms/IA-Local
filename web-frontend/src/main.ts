/**
 * Ponto de Entrada Modular do SDK Frontend TypeScript da AURA (P2-6).
 * Exporta contratos estaticos, validadores em runtime e acopla de forma compativel
 * ao escopo global window.AuraSDK para coexistencia progressiva com a SPA.
 * Zero travessoes em todo o arquivo.
 */

import {
  AuraApiClient,
  type AuraClientConfig,
  isValidActionVoucher,
  isValidGenUIEnvelope,
} from "./api/aura-client";

export * from "./types/aura-contracts";
export {
  AuraApiClient,
  type AuraClientConfig,
  isValidActionVoucher,
  isValidGenUIEnvelope,
};

export interface AuraFrontendSDK {
  version: string;
  createClient: (config?: AuraClientConfig) => AuraApiClient;
  isValidGenUIEnvelope: typeof isValidGenUIEnvelope;
  isValidActionVoucher: typeof isValidActionVoucher;
}

export const auraFrontendSDK: AuraFrontendSDK = {
  version: "1.0.0",
  createClient: (config?: AuraClientConfig) => new AuraApiClient(config),
  isValidGenUIEnvelope,
  isValidActionVoucher,
};

declare global {
  interface Window {
    AuraSDK?: AuraFrontendSDK;
  }
}

if (typeof window !== "undefined") {
  window.AuraSDK = auraFrontendSDK;
}
