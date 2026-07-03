import { useState } from 'react'
import { calculateSeverance } from '../api'
import type { SeveranceResponse } from '../types'

const REASONS = [
  { value: 'efisiensi_tutup', label: 'Efisiensi / Penutupan' },
  { value: 'efisiensi_rugi', label: 'Efisiensi / Rugi 2 Tahun' },
  { value: 'penggabungan', label: 'Penggabungan (Merger)' },
  { value: 'pengambilalihan_tidak_bersedia', label: 'Pengambilalihan (Tidak Bersedia)' },
  { value: 'pengambilalihan_bersedia', label: 'Pengambilalihan (Bersedia)' },
  { value: 'pailit', label: 'Pailit' },
  { value: 'pelanggaran_pengusaha', label: 'Pelanggaran Pengusaha' },
  { value: 'pelanggaran_pekerja', label: 'Pelanggaran Pekerja' },
  { value: 'pengunduran_diri', label: 'Pengunduran Diri' },
  { value: 'mangkir_5_hari', label: 'Mangkir 5 Hari' },
  { value: 'penahanan', label: 'Penahanan Pidana' },
  { value: 'cacat_sakit_berkepanjangan', label: 'Cacat / Sakit Berkepanjangan' },
  { value: 'pensiun', label: 'Pensiun' },
  { value: 'meninggal', label: 'Meninggal Dunia' },
  { value: 'force_majeure', label: 'Force Majeure' },
]

function formatRp(n: number) {
  return `Rp ${n.toLocaleString('id-ID')}`
}

export default function Calculator() {
  const [masaKerja, setMasaKerja] = useState(5)
  const [gajiPokok, setGajiPokok] = useState(10000000)
  const [tunjangan, setTunjangan] = useState(0)
  const [alasan, setAlasan] = useState('efisiensi_tutup')
  const [result, setResult] = useState<SeveranceResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleCalculate(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const res = await calculateSeverance({
        masa_kerja_bulan: masaKerja * 12,
        upah_pokok: gajiPokok,
        tunjangan_tetap: tunjangan,
        alasan_phk: alasan,
      })
      setResult(res)
    } catch {
      setError('Gagal menghitung. Coba lagi.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-semibold text-gray-900 mb-1">Kalkulator Pesangon</h1>
      <p className="text-sm text-gray-500 mb-6">PP 35/2021 Pasal 40-59 (post-Cipta Kerja)</p>

      <form onSubmit={handleCalculate} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Masa Kerja (tahun)</label>
          <input
            type="number"
            min={0}
            max={40}
            value={masaKerja}
            onChange={e => setMasaKerja(Number(e.target.value))}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Gaji Pokok (Rp)</label>
          <input
            type="number"
            min={0}
            step={500000}
            value={gajiPokok}
            onChange={e => setGajiPokok(Number(e.target.value))}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Tunjangan Tetap (Rp)</label>
          <input
            type="number"
            min={0}
            step={500000}
            value={tunjangan}
            onChange={e => setTunjangan(Number(e.target.value))}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Alasan PHK</label>
          <select
            value={alasan}
            onChange={e => setAlasan(e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {REASONS.map(r => (
              <option key={r.value} value={r.value}>{r.label}</option>
            ))}
          </select>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-lg bg-gray-900 py-2.5 text-sm font-medium text-white hover:bg-gray-800 disabled:opacity-50"
        >
          {loading ? 'Menghitung...' : 'Hitung Pesangon'}
        </button>
      </form>

      {error && (
        <div className="mt-4 text-sm text-red-600 bg-red-50 rounded-lg p-3">{error}</div>
      )}

      {result && (
        <div className="mt-6 border border-gray-200 rounded-lg overflow-hidden">
          <div className="bg-gray-50 px-4 py-3 border-b border-gray-200">
            <span className="text-lg font-semibold text-gray-900">Total: {formatRp(result.total)}</span>
          </div>

          <table className="w-full text-sm">
            <tbody>
              <tr className="border-b border-gray-100">
                <td className="px-4 py-2.5 text-gray-600">Uang Pesangon</td>
                <td className="px-4 py-2.5 text-right font-medium">{formatRp(result.pesangon.amount)}</td>
              </tr>
              <tr className="border-b border-gray-100">
                <td className="px-4 py-2.5 text-gray-400 text-xs pl-8">{result.pesangon.formula}</td>
                <td />
              </tr>
              <tr className="border-b border-gray-100">
                <td className="px-4 py-2.5 text-gray-600">Uang Penghargaan Masa Kerja</td>
                <td className="px-4 py-2.5 text-right font-medium">{formatRp(result.penghargaan.amount)}</td>
              </tr>
              <tr className="border-b border-gray-100">
                <td className="px-4 py-2.5 text-gray-400 text-xs pl-8">{result.penghargaan.formula}</td>
                <td />
              </tr>
              <tr className="border-b border-gray-100">
                <td className="px-4 py-2.5 text-gray-600">Uang Penggantian Hak</td>
                <td className="px-4 py-2.5 text-right font-medium">{formatRp(result.penggantian_hak.amount)}</td>
              </tr>
              <tr>
                <td className="px-4 py-2.5 text-gray-400 text-xs pl-8">{result.penggantian_hak.formula}</td>
                <td />
              </tr>
            </tbody>
          </table>

          <div className="bg-gray-50 px-4 py-3 border-t border-gray-200">
            <h4 className="text-xs font-semibold text-gray-500 uppercase mb-1">Dasar Hukum</h4>
            <ul className="space-y-0.5">
              {result.legal_basis.map((lb, i) => (
                <li key={i} className="text-xs text-blue-600">{lb.pasal} — <span className="text-gray-500">{lb.description}</span></li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  )
}
