import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import * as api from "./api";

vi.mock("./api", async () => {
  const actual = await vi.importActual<typeof api>("./api");
  return {
    ...actual,
    fetchAccounts: vi.fn(),
    fetchStatements: vi.fn(),
    createAccount: vi.fn(),
    transfer: vi.fn(),
  };
});

const mockAccounts: api.Account[] = [
  { id: 1, name: "Acme Ltd", currency: "NGN", balance: 750000, created_at: "2026-01-01" },
  { id: 2, name: "Vendor A", currency: "NGN", balance: 0, created_at: "2026-01-01" },
];

describe("App", () => {
  beforeEach(() => {
    vi.mocked(api.fetchAccounts).mockResolvedValue(mockAccounts);
    vi.mocked(api.fetchStatements).mockResolvedValue([]);
  });

  it("renders fetched accounts with formatted balances, excluding the system liquidity account", async () => {
    render(<App />);

    expect(await screen.findByText("Acme Ltd")).toBeInTheDocument();
    expect(screen.getByText("₦7500.00")).toBeInTheDocument();
    expect(screen.queryByText("System Liquidity")).not.toBeInTheDocument();
  });

  it("submits a transfer with a fresh idempotency key and refreshes the account list", async () => {
    vi.mocked(api.transfer).mockResolvedValue({ transaction_id: "abc-123", balance: 550000 });
    const user = userEvent.setup();

    render(<App />);
    await screen.findByText("Acme Ltd");

    await user.type(screen.getByPlaceholderText("From account ID"), "1");
    await user.type(screen.getByPlaceholderText("To account ID"), "2");
    await user.type(screen.getByPlaceholderText("Amount (NGN)"), "2000");
    await user.click(screen.getByText("Send"));

    await waitFor(() => expect(api.transfer).toHaveBeenCalledWith(1, 2, 200000, expect.any(String)));
    expect(api.fetchAccounts).toHaveBeenCalledTimes(2); // initial load + post-transfer refresh
  });

  it("shows the server's error message when a transfer is rejected", async () => {
    vi.mocked(api.transfer).mockRejectedValue({ response: { data: { message: "Insufficient funds." } } });
    const user = userEvent.setup();

    render(<App />);
    await screen.findByText("Acme Ltd");

    await user.type(screen.getByPlaceholderText("From account ID"), "1");
    await user.type(screen.getByPlaceholderText("To account ID"), "2");
    await user.type(screen.getByPlaceholderText("Amount (NGN)"), "999999");
    await user.click(screen.getByText("Send"));

    expect(await screen.findByText("Insufficient funds.")).toBeInTheDocument();
  });
});
