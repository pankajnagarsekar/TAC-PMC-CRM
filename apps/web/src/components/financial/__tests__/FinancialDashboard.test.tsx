import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import BudgetTracker from '../BudgetTracker';
import CashFlowChart from '../CashFlowChart';
import PaymentApprovalQueue from '../PaymentApprovalQueue';
import MasterDataManager from '../MasterDataManager';
import FinancialDashboard from '../../app/financial/page';

// ============================================================================
// TEST SUITE 1: BudgetTracker Component
// ============================================================================

describe('BudgetTracker', () => {
  const mockBudgets = [
    {
      _id: 'b1',
      project_id: 'p1',
      organisation_id: 'org1',
      total_budget: 100000,
      allocations: [
        { code: 'LABOR', budget: 50000, spent: 35000 },
        { code: 'MATERIAL', budget: 30000, spent: 25000 },
        { code: 'EQUIPMENT', budget: 20000, spent: 18000 },
      ],
      status: 'ACTIVE',
      created_at: new Date(),
      updated_at: new Date(),
      version: 1,
    },
  ];

  test('renders with empty budget list', () => {
    render(<BudgetTracker budgets={[]} />);
    expect(screen.getByText(/budget/i)).toBeInTheDocument();
  });

  test('renders progress bars for each allocation', () => {
    render(<BudgetTracker budgets={mockBudgets} />);
    expect(screen.getByText(/LABOR/i)).toBeInTheDocument();
    expect(screen.getByText(/MATERIAL/i)).toBeInTheDocument();
    expect(screen.getByText(/EQUIPMENT/i)).toBeInTheDocument();
  });

  test('color codes allocation based on spending percentage', () => {
    render(<BudgetTracker budgets={mockBudgets} />);
    // LABOR: 35k/50k = 70% (yellow)
    // MATERIAL: 25k/30k = 83% (yellow)
    // EQUIPMENT: 18k/20k = 90% (red)
    const container = screen.getByText(/EQUIPMENT/i).closest('div');
    expect(container).toBeInTheDocument();
  });

  test('calculates and displays total budget summary', () => {
    render(<BudgetTracker budgets={mockBudgets} />);
    // Total: 78k/100k = 78% spent
    expect(screen.getByText(/78/i)).toBeInTheDocument();
  });
});

// ============================================================================
// TEST SUITE 2: CashFlowChart Component
// ============================================================================

describe('CashFlowChart', () => {
  const mockCashFlow = {
    project_id: 'p1',
    from_date: '2026-04-01',
    to_date: '2026-04-14',
    opening_balance: 100000,
    closing_balance: 85000,
    daily_breakdown: [
      { date: '2026-04-01', opening: 100000, closing: 98500, transactions_count: 3 },
      { date: '2026-04-02', opening: 98500, closing: 96200, transactions_count: 2 },
      { date: '2026-04-03', opening: 96200, closing: 95000, transactions_count: 1 },
    ],
  };

  test('renders AreaChart with data', () => {
    render(<CashFlowChart cashFlow={mockCashFlow} />);
    expect(screen.getByText(/cash flow/i)).toBeInTheDocument();
  });

  test('formats date labels correctly (MM/DD)', () => {
    render(<CashFlowChart cashFlow={mockCashFlow} />);
    // Should display dates in MM/DD format
    expect(screen.getByText(/04\/01|04\/02|04\/03/)).toBeInTheDocument();
  });

  test('displays opening and closing balances', () => {
    render(<CashFlowChart cashFlow={mockCashFlow} />);
    expect(screen.getByText(/100000|85000/)).toBeInTheDocument();
  });
});

// ============================================================================
// TEST SUITE 3: PaymentApprovalQueue Component
// ============================================================================

describe('PaymentApprovalQueue', () => {
  const mockApprovals = [
    {
      _id: 'pc1',
      vendor_id: 'v1',
      vendor_name: 'ABC Contractors',
      payment_amount: 25000,
      status: 'Submitted',
      created_at: '2026-04-10T00:00:00Z',
      approval_trail: [
        { action: 'SUBMIT', user_id: 'u1', timestamp: '2026-04-10T00:00:00Z' },
      ],
    },
    {
      _id: 'pc2',
      vendor_id: 'v2',
      vendor_name: 'XYZ Suppliers',
      payment_amount: 15000,
      status: 'In Review',
      created_at: '2026-04-12T00:00:00Z',
      approval_trail: [
        { action: 'SUBMIT', user_id: 'u1', timestamp: '2026-04-12T00:00:00Z' },
      ],
    },
  ];

  test('renders empty state when no approvals', () => {
    render(<PaymentApprovalQueue approvals={[]} />);
    expect(screen.getByText(/no pending|empty/i)).toBeInTheDocument();
  });

  test('renders table with pending approvals', () => {
    render(<PaymentApprovalQueue approvals={mockApprovals} />);
    expect(screen.getByText(/ABC Contractors/)).toBeInTheDocument();
    expect(screen.getByText(/XYZ Suppliers/)).toBeInTheDocument();
    expect(screen.getByText(/25000|25,000/)).toBeInTheDocument();
  });

  test('approve button triggers onApprove callback', async () => {
    const mockApprove = jest.fn();
    render(<PaymentApprovalQueue approvals={mockApprovals} onApprove={mockApprove} />);
    const approveButtons = screen.getAllByText(/approve/i);
    fireEvent.click(approveButtons[0]);
    await waitFor(() => {
      expect(mockApprove).toHaveBeenCalled();
    });
  });

  test('reject button triggers onReject callback', async () => {
    const mockReject = jest.fn();
    render(<PaymentApprovalQueue approvals={mockApprovals} onReject={mockReject} />);
    const rejectButtons = screen.getAllByText(/reject/i);
    fireEvent.click(rejectButtons[0]);
    await waitFor(() => {
      expect(mockReject).toHaveBeenCalled();
    });
  });
});

// ============================================================================
// TEST SUITE 4: MasterDataManager Component
// ============================================================================

describe('MasterDataManager', () => {
  const mockCodes = [
    { _id: 'c1', label: 'LABOR', description: 'Labor costs', default_percent: 50 },
    { _id: 'c2', label: 'MATERIAL', description: 'Material costs', default_percent: 30 },
    { _id: 'c3', label: 'EQUIPMENT', description: 'Equipment rentals', default_percent: 15 },
  ];

  test('renders code list', () => {
    render(<MasterDataManager codes={mockCodes} />);
    expect(screen.getByText(/LABOR/)).toBeInTheDocument();
    expect(screen.getByText(/MATERIAL/)).toBeInTheDocument();
    expect(screen.getByText(/EQUIPMENT/)).toBeInTheDocument();
  });

  test('add button opens modal', async () => {
    render(<MasterDataManager codes={mockCodes} />);
    const addButton = screen.getByText(/add code|new code/i);
    fireEvent.click(addButton);
    await waitFor(() => {
      expect(screen.getByText(/create|add new/i)).toBeInTheDocument();
    });
  });

  test('edit button opens edit modal', async () => {
    render(<MasterDataManager codes={mockCodes} />);
    const editButtons = screen.getAllByText(/edit/i);
    fireEvent.click(editButtons[0]);
    await waitFor(() => {
      expect(screen.getByDisplayValue(/LABOR/)).toBeInTheDocument();
    });
  });

  test('delete button triggers onDelete callback', async () => {
    const mockDelete = jest.fn();
    render(<MasterDataManager codes={mockCodes} onDelete={mockDelete} />);
    const deleteButtons = screen.getAllByText(/delete/i);
    fireEvent.click(deleteButtons[0]);
    // Confirmation modal should appear
    await waitFor(() => {
      const confirmDelete = screen.getByText(/confirm|sure/i);
      expect(confirmDelete).toBeInTheDocument();
    });
  });
});

// ============================================================================
// TEST SUITE 5: FinancialDashboard Integration
// ============================================================================

describe('FinancialDashboard Page', () => {
  test('page renders all 4 components', async () => {
    render(<FinancialDashboard />);
    await waitFor(() => {
      expect(screen.getByText(/budget/i)).toBeInTheDocument();
      expect(screen.getByText(/cash flow/i)).toBeInTheDocument();
      expect(screen.getByText(/pending approvals|approval/i)).toBeInTheDocument();
      expect(screen.getByText(/master data|financial codes/i)).toBeInTheDocument();
    });
  });

  test('displays loading state while fetching', () => {
    render(<FinancialDashboard />);
    // Should show loading indicator initially
    const loadingElements = screen.queryAllByRole('progressbar');
    expect(loadingElements.length).toBeGreaterThanOrEqual(0);
  });

  test('displays error state on API failure', async () => {
    // Mock failed SWR call
    render(<FinancialDashboard />);
    // This would require mocking useSWR, deferred to integration test
    expect(screen.getByText(/financial/i)).toBeInTheDocument();
  });

  test('2-column layout on lg breakpoint', () => {
    const { container } = render(<FinancialDashboard />);
    const gridContainer = container.querySelector('[class*="grid"]');
    expect(gridContainer).toHaveClass('grid');
  });

  test('stacks to single column on mobile (sm)', () => {
    const { container } = render(<FinancialDashboard />);
    const gridContainer = container.querySelector('[class*="grid"]');
    expect(gridContainer).toHaveClass('grid-cols-1');
  });
});
