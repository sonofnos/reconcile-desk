import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8234/api";

export const api = axios.create({ baseURL: API_BASE_URL });

export interface Account {
  id: number;
  name: string;
  currency: string;
  balance: number;
  created_at: string;
}

export interface StatementLine {
  id: number;
  external_reference: string;
  date: string;
  amount: number;
  description: string;
  status: "MATCHED" | "AMOUNT_MISMATCH" | "MISSING_IN_LEDGER";
}

export interface StatementImport {
  id: number;
  filename: string;
  uploaded_at: string;
  lines: StatementLine[];
}

export async function fetchAccounts(): Promise<Account[]> {
  const { data } = await api.get<Account[]>("/accounts/");
  return data;
}

export async function createAccount(name: string, currency: string): Promise<Account> {
  const { data } = await api.post<Account>("/accounts/", { name, currency });
  return data;
}

export async function transfer(
  fromAccount: number,
  toAccount: number,
  amountMinorUnits: number,
  idempotencyKey: string
): Promise<{ transaction_id: string; balance: number }> {
  const { data } = await api.post(
    "/transfers/",
    { from_account: fromAccount, to_account: toAccount, amount: amountMinorUnits },
    { headers: { "Idempotency-Key": idempotencyKey } }
  );
  return data;
}

export async function uploadStatement(file: File): Promise<StatementImport> {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await api.post<StatementImport>("/statements/", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function fetchStatements(): Promise<StatementImport[]> {
  const { data } = await api.get<StatementImport[]>("/statements/");
  return data;
}

export function formatMoney(minorUnits: number, currency = "NGN"): string {
  const symbol = currency === "NGN" ? "₦" : currency + " ";
  return `${symbol}${(minorUnits / 100).toFixed(2)}`;
}
