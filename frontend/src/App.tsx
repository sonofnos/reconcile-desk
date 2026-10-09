import { useEffect, useState } from "react";
import "./App.css";
import {
  createAccount,
  fetchAccounts,
  fetchStatements,
  formatMoney,
  transfer,
  uploadStatement,
} from "./api";
import type { Account, StatementImport } from "./api";

function statusLabel(status: string): string {
  return status.replace(/_/g, " ");
}

function App() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [statements, setStatements] = useState<StatementImport[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const [newAccountName, setNewAccountName] = useState("");
  const [fromAccount, setFromAccount] = useState("");
  const [toAccount, setToAccount] = useState("");
  const [amount, setAmount] = useState("");

  async function refresh() {
    const [accs, stmts] = await Promise.all([fetchAccounts(), fetchStatements()]);
    setAccounts(accs);
    setStatements(stmts);
  }

  useEffect(() => {
    refresh()
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  async function handleCreateAccount(e: React.FormEvent) {
    e.preventDefault();
    if (!newAccountName.trim()) return;
    try {
      await createAccount(newAccountName.trim(), "NGN");
      setNewAccountName("");
      await refresh();
    } catch (err) {
      setError(String(err));
    }
  }

  async function handleTransfer(e: React.FormEvent) {
    e.preventDefault();
    const amountMinor = Math.round(parseFloat(amount) * 100);
    if (!fromAccount || !toAccount || !amountMinor) return;
    try {
      await transfer(Number(fromAccount), Number(toAccount), amountMinor, crypto.randomUUID());
      setAmount("");
      await refresh();
    } catch (err: any) {
      setError(err?.response?.data?.message || String(err));
    }
  }

  async function handleStatementUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      await uploadStatement(file);
      await refresh();
    } catch (err) {
      setError(String(err));
    }
    e.target.value = "";
  }

  if (loading) return <div className="container">Loading...</div>;

  return (
    <div className="container">
      <h1>ReconcileDesk</h1>
      {error && <div className="error-banner">{error}</div>}

      <section>
        <h2>Accounts</h2>
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Name</th>
              <th>Balance</th>
            </tr>
          </thead>
          <tbody>
            {accounts
              .filter((a) => a.name !== "System Liquidity")
              .map((a) => (
                <tr key={a.id}>
                  <td>{a.id}</td>
                  <td>{a.name}</td>
                  <td>{formatMoney(a.balance, a.currency)}</td>
                </tr>
              ))}
          </tbody>
        </table>
        <form onSubmit={handleCreateAccount} className="inline-form">
          <input
            placeholder="New account name"
            value={newAccountName}
            onChange={(e) => setNewAccountName(e.target.value)}
          />
          <button type="submit">Add account</button>
        </form>
      </section>

      <section>
        <h2>Transfer</h2>
        <form onSubmit={handleTransfer} className="inline-form">
          <input placeholder="From account ID" value={fromAccount} onChange={(e) => setFromAccount(e.target.value)} />
          <input placeholder="To account ID" value={toAccount} onChange={(e) => setToAccount(e.target.value)} />
          <input placeholder="Amount (NGN)" value={amount} onChange={(e) => setAmount(e.target.value)} />
          <button type="submit">Send</button>
        </form>
      </section>

      <section>
        <h2>Bank statement reconciliation</h2>
        <input type="file" accept=".csv" onChange={handleStatementUpload} />
        {statements.map((s) => (
          <div key={s.id} className="statement-block">
            <h3>{s.filename}</h3>
            <table>
              <thead>
                <tr>
                  <th>Reference</th>
                  <th>Date</th>
                  <th>Amount</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {s.lines.map((line) => (
                  <tr key={line.id} className={`status-${line.status.toLowerCase()}`}>
                    <td>{line.external_reference}</td>
                    <td>{line.date}</td>
                    <td>{formatMoney(line.amount)}</td>
                    <td>{statusLabel(line.status)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}
      </section>
    </div>
  );
}

export default App;
