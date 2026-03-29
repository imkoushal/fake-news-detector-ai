export default function Navbar() {
  return (
    <nav className="fixed top-0 left-0 w-full z-50 backdrop-blur-lg bg-white/10 border-b border-white/20">
      <div className="max-w-6xl mx-auto flex justify-between items-center px-6 py-4">
        
        {/* Logo */}
        <h1 className="text-xl font-bold">FakeNews AI</h1>

        {/* Links */}
        <div className="space-x-6 text-sm">
          <a href="#home" className="hover:text-purple-400">Home</a>
          <a href="#analyze" className="hover:text-purple-400">Analyze</a>
          <a href="#features" className="hover:text-purple-400">Features</a>
        </div>

      </div>
    </nav>
  );
}