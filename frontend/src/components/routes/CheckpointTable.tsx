import { formatDateTime } from '../../lib/format'
import { RISK_META } from '../../lib/risk'
import type { Checkpoint, RiskLevel } from '../../types/api'
import { RiskBadge } from '../ui/RiskBadge'

function Reading({ value, level }: { value: string; level: RiskLevel }) {
  return (
    <td
      className="px-2 py-1.5 text-right tabular-nums"
      style={level === 'low' ? undefined : { color: RISK_META[level].color, fontWeight: 600 }}
    >
      {value}
    </td>
  )
}

export function CheckpointTable({ checkpoints }: { checkpoints: Checkpoint[] }) {
  return (
    <div className="max-h-72 overflow-auto rounded-lg ring-1 ring-slate-200">
      <table className="w-full text-xs">
        <thead className="sticky top-0 bg-slate-50 text-slate-500">
          <tr>
            <th scope="col" className="px-2 py-1.5 text-left font-medium">Mile</th>
            <th scope="col" className="px-2 py-1.5 text-left font-medium">ETA</th>
            <th scope="col" className="px-2 py-1.5 text-right font-medium">Wind mph</th>
            <th scope="col" className="px-2 py-1.5 text-right font-medium">Rain in/h</th>
            <th scope="col" className="px-2 py-1.5 text-right font-medium">Snow in/h</th>
            <th scope="col" className="px-2 py-1.5 text-left font-medium">Risk</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 bg-white text-slate-700">
          {checkpoints.map((checkpoint) => (
            <tr key={checkpoint.sequence} title={checkpoint.reasons.join('\n') || undefined}>
              <td className="px-2 py-1.5 tabular-nums">{Math.round(checkpoint.distance_mi)}</td>
              <td className="px-2 py-1.5 whitespace-nowrap">{formatDateTime(checkpoint.eta)}</td>
              <Reading value={checkpoint.wind_mph.toFixed(0)} level={checkpoint.factors.wind} />
              <Reading value={checkpoint.rain_in_hr.toFixed(2)} level={checkpoint.factors.rain} />
              <Reading value={checkpoint.snow_in_hr.toFixed(2)} level={checkpoint.factors.snow} />
              <td className="px-2 py-1.5">
                <RiskBadge level={checkpoint.risk} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
