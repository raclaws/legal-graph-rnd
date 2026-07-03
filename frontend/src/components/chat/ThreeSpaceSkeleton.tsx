export default function ThreeSpaceSkeleton() {
  return (
    <div className="space-y-3 animate-pulse">
      <div className="border-l-4 border-blue-200 bg-blue-50/50 rounded-r-lg p-4">
        <div className="h-3 w-16 bg-blue-200 rounded mb-3" />
        <div className="space-y-2">
          <div className="h-3 w-full bg-blue-100 rounded" />
          <div className="h-3 w-3/4 bg-blue-100 rounded" />
          <div className="h-3 w-5/6 bg-blue-100 rounded" />
        </div>
      </div>
      <div className="border-l-4 border-amber-200 bg-amber-50/50 rounded-r-lg p-4">
        <div className="h-3 w-20 bg-amber-200 rounded mb-3" />
        <div className="space-y-2">
          <div className="h-3 w-full bg-amber-100 rounded" />
          <div className="h-3 w-2/3 bg-amber-100 rounded" />
        </div>
      </div>
    </div>
  )
}
