interface Props {
  onSelect: (text: string) => void
}

const ACTIONS = [
  { label: 'Cek PKWT saya', prefill: 'Saya punya PKWT yang sudah berjalan 3 tahun, apakah bisa diperpanjang?' },
  { label: 'Hitung pesangon', prefill: 'Hitung pesangon saya: masa kerja 5 tahun, gaji Rp 10 juta, PHK efisiensi' },
  { label: 'Cek BPJS', prefill: 'Berapa iuran BPJS yang harus dibayar perusahaan untuk gaji Rp 10 juta?' },
  { label: 'PHK karyawan', prefill: 'Apa prosedur PHK karyawan tetap yang benar menurut hukum?' },
  { label: 'Upah minimum', prefill: 'Berapa UMP DKI Jakarta 2025?' },
  { label: 'Jam kerja', prefill: 'Berapa jam kerja maksimal per minggu dan bagaimana aturan lembur?' },
]

export default function QuickActions({ onSelect }: Props) {
  return (
    <div className="flex flex-wrap justify-center gap-2">
      {ACTIONS.map(a => (
        <button
          key={a.label}
          onClick={() => onSelect(a.prefill)}
          className="rounded-full border border-gray-300 px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 hover:border-gray-400 transition-colors"
        >
          {a.label}
        </button>
      ))}
    </div>
  )
}
