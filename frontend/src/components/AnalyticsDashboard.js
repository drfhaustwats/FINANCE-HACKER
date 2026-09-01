import React, { useMemo } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

const CHART_COLORS = {
  spending: '#dc6b5f',
  income: '#3f9f78',
  refunds: '#4f83cc',
  net: '#8b6bb8',
  grid: '#526173',
  categories: ['#5684b8', '#5f9a82', '#9a7bb5', '#bd7c68', '#8a94a5', '#6f8f9f', '#9b8a67', '#7487b5'],
};

const AnalyticsDashboard = ({
  categoryBreakdown = [],
  monthlyReports = [],
  dashboardSummary,
  formatCurrency,
  getMonthName,
  onOpenCategory,
  onOpenReviewCenter,
}) => {
  const summary = dashboardSummary || {};

  const cashFlowData = useMemo(() => monthlyReports.map((report) => ({
    month: report.month,
    spending: Number(report.total_spent || 0),
    income: Number(report.total_income ?? report.total_received ?? 0),
    refunds: Number(report.total_refunds || 0),
    net: Number(report.net || 0),
    transactions: Number(report.transaction_count || 0),
  })), [monthlyReports]);

  const categoryData = useMemo(() => {
    const sorted = [...categoryBreakdown]
      .map((category) => ({
        name: category.category,
        amount: Number(category.amount || 0),
        count: Number(category.count || 0),
      }))
      .sort((left, right) => right.amount - left.amount);
    return sorted;
  }, [categoryBreakdown]);

  const excludedMovementTotal = Number(summary.total_transfer_in || 0)
    + Number(summary.total_transfer_out || 0)
    + Number(summary.total_credit_card_payments || 0)
    + Number(summary.total_investment_in || 0)
    + Number(summary.total_investment_out || 0);
  const surplusToIncomeRatio = Number(summary.total_income || 0) > 0
    ? (Number(summary.net || 0) / Number(summary.total_income || 0)) * 100
    : null;
  const topCategory = categoryData[0];
  const totalSpending = Number(summary.total_spent || 0);
  const netDisplay = Number(summary.net || 0);
  const accountBalanceMovement = Number(summary.gross_money_in || 0)
    - Number(summary.gross_money_out || 0);
  const tooltipCurrency = (value) => formatCurrency(Number(value || 0));

  return (
    <div className="space-y-6">
      <section className="bg-white rounded-lg shadow p-5" aria-labelledby="analytics-heading">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 id="analytics-heading" className="text-xl font-bold text-gray-900">Financial Analytics</h2>
            <p className="text-sm text-gray-500 mt-1">
              Purchases, income, refunds, and money movements are classified separately.
            </p>
          </div>
          <p className="text-sm text-gray-500">
            {summary.currency || 'CAD'} · {summary.period === 'year_to_date' ? `${summary.year} year to date` : summary.year || 'Selected period'}
            {summary.period_end ? ` · through ${summary.period_end}` : ''}
          </p>
        </div>
      </section>

      <section className="grid grid-cols-2 lg:grid-cols-4 gap-4" aria-label="Financial summary">
        <div className="bg-white rounded-lg shadow p-5">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">Purchase Spending</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{formatCurrency(totalSpending)}</p>
          <p className="text-xs text-gray-500">Transfers and card payments excluded</p>
        </div>
        <div className="bg-white rounded-lg shadow p-5">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">Income</p>
          <p className="text-2xl font-bold text-green-600 mt-1">{formatCurrency(summary.total_income || 0)}</p>
          <p className="text-xs text-gray-500">Refunds shown separately</p>
        </div>
        <div className="bg-white rounded-lg shadow p-5">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">Classified Surplus</p>
          <p className={`text-2xl font-bold mt-1 ${netDisplay >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            {netDisplay >= 0 ? '+' : '-'}{formatCurrency(Math.abs(netDisplay))}
          </p>
          <p className="text-xs text-gray-500">Income + refunds minus purchases; not a balance change</p>
        </div>
        <div className="bg-white rounded-lg shadow p-5">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">Excluded Movements</p>
          <p className="text-2xl font-bold text-blue-600 mt-1">{formatCurrency(excludedMovementTotal)}</p>
          <p className="text-xs text-gray-500">Transfers, investments, card payments</p>
        </div>
      </section>

      <section className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="mb-5">
            <h3 className="text-lg font-medium text-gray-900">Monthly Purchase Surplus</h3>
            <p className="text-sm text-gray-500">Income and refunds compared with purchases; transfers and card payments are separate.</p>
          </div>
          {cashFlowData.length > 0 ? (
            <>
              <div className="h-80" role="img" aria-label="Monthly income, refunds, spending, and classified surplus chart">
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={cashFlowData} margin={{ top: 12, right: 16, bottom: 12, left: 8 }} accessibilityLayer>
                    <CartesianGrid stroke={CHART_COLORS.grid} strokeOpacity={0.25} vertical={false} />
                    <XAxis dataKey="month" tickFormatter={(month) => getMonthName(month).slice(0, 3)} tick={{ fontSize: 12 }} />
                    <YAxis tickFormatter={(value) => `$${Math.round(value / 1000)}k`} width={54} tick={{ fontSize: 12 }} />
                    <Tooltip formatter={(value, name) => [tooltipCurrency(value), name]} labelFormatter={(month) => getMonthName(month)} />
                    <Legend />
                    <Bar dataKey="spending" name="Spending" fill={CHART_COLORS.spending} radius={[3, 3, 0, 0]} />
                    <Bar dataKey="income" name="Income" fill={CHART_COLORS.income} radius={[3, 3, 0, 0]} />
                    <Bar dataKey="refunds" name="Refunds" fill={CHART_COLORS.refunds} radius={[3, 3, 0, 0]} />
                    <Line dataKey="net" name="Surplus" stroke={CHART_COLORS.net} strokeWidth={3} dot={{ r: 3 }} />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
              <div className="overflow-x-auto mt-4">
                <table className="min-w-full text-xs" aria-label="Monthly cash flow values">
                  <thead className="text-gray-500">
                    <tr>
                      <th className="text-left py-1 pr-3">Month</th>
                      <th className="text-right px-2">Spending</th>
                      <th className="text-right px-2">Income</th>
                      <th className="text-right px-2">Refunds</th>
                      <th className="text-right pl-2">Surplus</th>
                    </tr>
                  </thead>
                  <tbody className="text-gray-700">
                    {cashFlowData.map((row) => (
                      <tr key={row.month} className="border-t border-gray-100">
                        <td className="py-1 pr-3">{getMonthName(row.month)}</td>
                        <td className="text-right px-2">{formatCurrency(row.spending)}</td>
                        <td className="text-right px-2">{formatCurrency(row.income)}</td>
                        <td className="text-right px-2">{formatCurrency(row.refunds)}</td>
                        <td className="text-right pl-2">{row.net >= 0 ? '+' : '-'}{formatCurrency(Math.abs(row.net))}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          ) : (
            <p className="text-sm text-gray-500 py-16 text-center">No monthly data available.</p>
          )}
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="mb-5">
            <h3 className="text-lg font-medium text-gray-900">Spending by Category</h3>
            <p className="text-sm text-gray-500">Purchase spending only; transfer categories are excluded. Select a bar to open its year-to-date transactions.</p>
          </div>
          {categoryData.length > 0 ? (
            <>
              <div className="h-96" role="img" aria-label="Purchase spending by category chart">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={categoryData} layout="vertical" margin={{ top: 4, right: 28, bottom: 4, left: 32 }} accessibilityLayer>
                    <CartesianGrid stroke={CHART_COLORS.grid} strokeOpacity={0.2} horizontal={false} />
                    <XAxis type="number" tickFormatter={(value) => `$${Math.round(value / 1000)}k`} tick={{ fontSize: 12 }} />
                    <YAxis type="category" dataKey="name" width={150} tick={{ fontSize: 11 }} />
                    <Tooltip formatter={(value) => [tooltipCurrency(value), 'Spending']} />
                    <Bar dataKey="amount" name="Spending" radius={[0, 4, 4, 0]}>
                      {categoryData.map((category, index) => (
                        <Cell
                          key={category.name}
                          fill={CHART_COLORS.categories[index % CHART_COLORS.categories.length]}
                          cursor={onOpenCategory ? 'pointer' : 'default'}
                          onClick={() => onOpenCategory?.(category.name)}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div className="mt-4 max-h-48 divide-y divide-gray-100 overflow-y-auto border-t border-gray-100" aria-label="Category transaction links">
                {categoryData.map((category) => (
                  <button
                    key={category.name}
                    type="button"
                    onClick={() => onOpenCategory?.(category.name)}
                    className="flex w-full items-center justify-between px-2 py-2 text-left text-sm hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-500"
                  >
                    <span className="font-medium text-gray-800">{category.name}</span>
                    <span className="ml-4 whitespace-nowrap text-gray-600">{formatCurrency(category.amount)} · {category.count.toLocaleString()} transactions</span>
                  </button>
                ))}
              </div>
            </>
          ) : (
            <p className="text-sm text-gray-500 py-16 text-center">No purchase spending in this period.</p>
          )}
        </div>
      </section>

      <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Flow Reconciliation</h3>
          <dl className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
            <div className="col-span-2 rounded-md bg-gray-50 px-3 py-2">
              <dt className="text-gray-500">Posted ledger movement</dt>
              <dd className={`font-semibold ${accountBalanceMovement >= 0 ? 'text-green-700' : 'text-red-700'}`}>
                {accountBalanceMovement >= 0 ? '+' : '-'}{formatCurrency(Math.abs(accountBalanceMovement))}
              </dd>
              <p className="mt-1 text-xs text-gray-500">Gross recorded credits minus debits; transfers included, pending activity excluded.</p>
            </div>
            <div><dt className="text-gray-500">Gross recorded debits</dt><dd className="font-semibold text-gray-900">{formatCurrency(summary.gross_money_out || 0)}</dd></div>
            <div><dt className="text-gray-500">Gross recorded credits</dt><dd className="font-semibold text-gray-900">{formatCurrency(summary.gross_money_in || 0)}</dd></div>
            <div><dt className="text-gray-500">Transfers out</dt><dd className="font-semibold text-gray-900">{formatCurrency(summary.total_transfer_out || 0)}</dd></div>
            <div><dt className="text-gray-500">Transfers in</dt><dd className="font-semibold text-gray-900">{formatCurrency(summary.total_transfer_in || 0)}</dd></div>
            <div><dt className="text-gray-500">Credit-card payments</dt><dd className="font-semibold text-gray-900">{formatCurrency(summary.total_credit_card_payments || 0)}</dd></div>
            <div><dt className="text-gray-500">Investment movements</dt><dd className="font-semibold text-gray-900">{formatCurrency(Number(summary.total_investment_in || 0) + Number(summary.total_investment_out || 0))}</dd></div>
            <div><dt className="text-gray-500">Refunds and credits</dt><dd className="font-semibold text-gray-900">{formatCurrency(summary.total_refunds || 0)}</dd></div>
          </dl>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Verified Insights</h3>
          <ul className="space-y-3 text-sm text-gray-700">
            {surplusToIncomeRatio !== null && (
              <li>
                Classified surplus is <span className="font-semibold">{surplusToIncomeRatio.toFixed(1)}%</span> of classified income for this period.
                {' '}This is not a savings rate or bank-balance change.
              </li>
            )}
            {topCategory && totalSpending > 0 && (
              <li>
                <span className="font-semibold">{topCategory.name}</span> is the largest purchase category at{' '}
                <span className="font-semibold">{((topCategory.amount / totalSpending) * 100).toFixed(1)}%</span> of spending.
              </li>
            )}
            <li>
              <span className="font-semibold">{Number(summary.source_transaction_count || 0).toLocaleString()}</span> records fall in the selected period;{' '}
              <span className="font-semibold">{Number(summary.transaction_count || 0).toLocaleString()}</span> posted {summary.currency || 'CAD'} records feed its totals, and{' '}
              <span className="font-semibold">{Number(summary.all_transaction_count || 0).toLocaleString()}</span> records exist in this data scope overall.
            </li>
            {Number(summary.pending_count || 0) > 0 && (
              <li>
                {Number(summary.pending_count).toLocaleString()} pending transactions are excluded until the institution posts or removes them. Pending {summary.currency || 'CAD'} movement is {formatCurrency(Number(summary.pending_money_out || 0))} out / {formatCurrency(Number(summary.pending_money_in || 0))} in.
              </li>
            )}
            {(Number(summary.classification_review_count || 0) > 0 || Number(summary.ambiguous_transfer_review_count || 0) > 0) && (
              <li>
                {Number(summary.classification_review_count || 0) > 0 && (
                  <span>{Number(summary.classification_review_count).toLocaleString()} legacy provider transfer flags remain unresolved after verified account pairing. </span>
                )}
                {Number(summary.ambiguous_transfer_review_count || 0) > 0 && (
                  <span>{Number(summary.ambiguous_transfer_review_count).toLocaleString()} entries have multiple eligible equal-amount cross-account matches. No internal pair was assumed. </span>
                )}
                {onOpenReviewCenter && (
                  <button
                    type="button"
                    onClick={onOpenReviewCenter}
                    className="underline text-amber-800 hover:text-amber-900 focus:outline-none focus:ring-1 focus:ring-amber-600 rounded"
                  >
                    Open Review Center
                  </button>
                )}
              </li>
            )}
            {Number(summary.matched_internal_transfer_count || 0) > 0 && (
              <li>
                {summary.matched_internal_transfer_count / 2} internal transfer pairs were verified from opposite entries on different identified accounts.
              </li>
            )}
            {excludedMovementTotal > 0 && (
              <li>{formatCurrency(excludedMovementTotal)} of transfers, investments, and card payments was kept outside purchase and income totals.</li>
            )}
            {Number(summary.foreign_currency_count || 0) > 0 && (
              <li>{summary.foreign_currency_count} non-{summary.currency || 'CAD'} transactions are excluded from monetary totals.</li>
            )}
          </ul>
        </div>
      </section>
    </div>
  );
};

export default AnalyticsDashboard;
