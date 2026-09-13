import { useEffect, useState } from 'react';
import { Routes, Route, Link, useLocation, useNavigate } from 'react-router-dom';
import liff from '@line/liff';
import { Users, ShoppingBag, QrCode, Settings, ChevronLeft, ShieldCheck, Zap } from 'lucide-react';
import { motion } from 'framer-motion';

const COMPANY_LIFF_IDS = {
  'pro_nexus': '2011564874-MNIECumQ',
  'tp_extra': '2011576094-vwbg5mee',
  'luck_kio': '2011579873-asAQ8pxU',
  'peak_icon': '2011580328-yWlEyeOK'
};

// URL ของ API หลังบ้าน (FastAPI บน Railway)
const BACKEND_URL = 'https://pro-nexus-os-production.up.railway.app';

const pageTransition = {
  initial: { opacity: 0, y: 15 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -15 },
  transition: { duration: 0.3 }
};

const BackButton = () => (
  <div className="text-center mt-8">
    <Link to="/" className="inline-flex items-center justify-center px-6 py-3 bg-gray-900 text-white rounded-2xl font-medium text-sm shadow-lg hover:bg-gray-800 hover:shadow-xl transition-all active:scale-95">
      <ChevronLeft className="w-4 h-4 mr-1" /> เมนูหลัก
    </Link>
  </div>
);

const TeamUI = () => (
  <motion.div {...pageTransition} className="p-6">
    <div className="bg-white/80 backdrop-blur-xl rounded-3xl shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-white p-6">
      <div className="flex items-center space-x-4 mb-6">
        <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-indigo-500 to-blue-600 flex items-center justify-center text-white shadow-indigo-200 shadow-lg"><Users className="w-6 h-6" /></div>
        <div><h2 className="text-xl font-bold text-gray-800">ระบบจัดการทีม</h2><p className="text-sm text-gray-500">RBAC & โครงสร้างสายงาน</p></div>
      </div>
      <div className="bg-gray-50/50 p-6 rounded-2xl border border-gray-100 text-center flex flex-col items-center justify-center h-40">
        <ShieldCheck className="w-8 h-8 text-indigo-300 mb-3" />
        <p className="text-gray-500 text-sm font-medium">รอเชื่อมต่อฐานข้อมูลรายชื่อ</p>
      </div>
    </div>
    <BackButton />
  </motion.div>
);

const ShopUI = () => (
  <motion.div {...pageTransition} className="p-6">
    <div className="bg-white/80 backdrop-blur-xl rounded-3xl shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-white p-6">
      <div className="flex items-center space-x-4 mb-6">
        <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-emerald-400 to-teal-500 flex items-center justify-center text-white shadow-emerald-200 shadow-lg"><ShoppingBag className="w-6 h-6" /></div>
        <div><h2 className="text-xl font-bold text-gray-800">ร้านค้าแพ็กเกจ</h2><p className="text-sm text-gray-500">เลือกอัปเกรดระบบของคุณ</p></div>
      </div>
      <div className="grid grid-cols-1 gap-4">
        <div className="group border border-gray-100 rounded-2xl p-5 bg-white hover:border-emerald-500 hover:shadow-lg transition-all cursor-pointer">
          <div className="flex justify-between items-center"><div><h3 className="font-bold text-gray-800 text-lg">Pro Package</h3><p className="text-xs text-gray-500">ฟังก์ชันพื้นฐาน</p></div><span className="text-emerald-600 font-extrabold">฿990</span></div>
        </div>
      </div>
    </div>
    <BackButton />
  </motion.div>
);

const QrCodeUI = () => (
  <motion.div {...pageTransition} className="p-6">
    <div className="bg-white/80 backdrop-blur-xl rounded-3xl shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-white p-6 text-center">
      <div className="inline-flex w-12 h-12 rounded-2xl bg-gradient-to-br from-amber-400 to-orange-500 items-center justify-center text-white shadow-amber-200 shadow-lg mb-4"><QrCode className="w-6 h-6" /></div>
      <h2 className="text-xl font-bold text-gray-800 mb-1">QR Code ของคุณ</h2>
      <p className="text-sm text-gray-500 mb-6">ใช้สำหรับสแกนจ่ายหรือเชิญเข้าทีม</p>
      <div className="w-56 h-56 mx-auto bg-gray-50 rounded-3xl border-2 border-dashed border-gray-200 flex items-center justify-center mb-6 relative overflow-hidden">
        <QrCode className="w-20 h-20 text-gray-300" />
      </div>
      <button className="w-full py-4 bg-gray-900 text-white rounded-2xl font-semibold shadow-xl hover:bg-gray-800 active:scale-95 transition-all flex justify-center items-center"><QrCode className="w-5 h-5 mr-2" /> สแกน QR Code อื่น</button>
    </div>
    <BackButton />
  </motion.div>
);

const SuperAdminUI = () => (
  <motion.div {...pageTransition} className="p-6">
    <div className="bg-white/80 backdrop-blur-xl rounded-3xl shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-white p-6">
      <div className="flex items-center space-x-4 mb-8">
        <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-red-500 to-rose-600 flex items-center justify-center text-white shadow-red-200 shadow-lg"><Settings className="w-6 h-6" /></div>
        <div><h2 className="text-xl font-bold text-gray-800">Super Admin</h2><p className="text-sm text-gray-500">ตั้งค่าระบบส่วนกลาง</p></div>
      </div>
      <div className="space-y-4">
        <div className="flex items-center justify-between p-4 bg-gray-50 rounded-2xl border border-gray-100">
          <div><h3 className="font-bold text-gray-800 text-sm">ระบบจ่าย Referral</h3><p className="text-xs text-gray-500">โบนัสแนะนำสมาชิก</p></div>
          <div className="w-12 h-6 bg-green-500 rounded-full relative shadow-inner"><div className="w-5 h-5 bg-white rounded-full absolute top-0.5 right-0.5 shadow-sm"></div></div>
        </div>
      </div>
    </div>
    <BackButton />
  </motion.div>
);

const Home = ({ profile, companyKey }) => (
  <motion.div {...pageTransition} className="p-6">
    <div className="bg-white/80 backdrop-blur-xl rounded-3xl shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-white p-5 mb-8 flex items-center space-x-4">
      {profile ? (
        <>
          <img src={profile.pictureUrl} alt="Profile" className="w-16 h-16 rounded-2xl object-cover shadow-sm" />
          <div>
            <h2 className="font-bold text-gray-800 text-lg tracking-tight">{profile.displayName}</h2>
            <div className="flex items-center mt-1">
              <span className="flex items-center text-xs font-semibold text-emerald-600 bg-emerald-50 px-2 py-1 rounded-lg"><ShieldCheck className="w-3 h-3 mr-1" /> Verified</span>
              <span className="ml-2 text-[10px] text-gray-400 font-medium uppercase tracking-wider bg-gray-100 px-2 py-1 rounded-lg">{companyKey.replace('_', ' ')}</span>
            </div>
          </div>
        </>
      ) : (
        <div className="animate-pulse flex items-center space-x-4 w-full">
          <div className="w-16 h-16 bg-gray-200 rounded-2xl"></div>
          <div className="space-y-3 flex-1"><div className="h-4 bg-gray-200 rounded-md w-1/2"></div></div>
        </div>
      )}
    </div>

    <div className="grid grid-cols-2 gap-4">
      <Link to="/team" className="group bg-white rounded-3xl p-5 shadow-[0_4px_20px_rgb(0,0,0,0.03)] border border-gray-50 hover:shadow-lg hover:border-indigo-100 transition-all active:scale-95 flex flex-col items-center text-center">
        <div className="w-14 h-14 bg-indigo-50 text-indigo-600 rounded-2xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform"><Users className="w-7 h-7" /></div>
        <h3 className="font-bold text-gray-800 text-sm">จัดการทีม</h3><p className="text-[11px] text-gray-400 mt-1">สิทธิ์ & สายงาน</p>
      </Link>
      <Link to="/shop" className="group bg-white rounded-3xl p-5 shadow-[0_4px_20px_rgb(0,0,0,0.03)] border border-gray-50 hover:shadow-lg hover:border-emerald-100 transition-all active:scale-95 flex flex-col items-center text-center">
        <div className="w-14 h-14 bg-emerald-50 text-emerald-600 rounded-2xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform"><ShoppingBag className="w-7 h-7" /></div>
        <h3 className="font-bold text-gray-800 text-sm">ร้านค้า</h3><p className="text-[11px] text-gray-400 mt-1">แพ็กเกจระบบ</p>
      </Link>
      <Link to="/qrcode" className="group bg-white rounded-3xl p-5 shadow-[0_4px_20px_rgb(0,0,0,0.03)] border border-gray-50 hover:shadow-lg hover:border-amber-100 transition-all active:scale-95 flex flex-col items-center text-center">
        <div className="w-14 h-14 bg-amber-50 text-amber-600 rounded-2xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform"><QrCode className="w-7 h-7" /></div>
        <h3 className="font-bold text-gray-800 text-sm">QR Code</h3><p className="text-[11px] text-gray-400 mt-1">สแกน & ชำระเงิน</p>
      </Link>
      <Link to="/admin" className="group bg-white rounded-3xl p-5 shadow-[0_4px_20px_rgb(0,0,0,0.03)] border border-gray-50 hover:shadow-lg hover:border-red-100 transition-all active:scale-95 flex flex-col items-center text-center">
        <div className="w-14 h-14 bg-red-50 text-red-600 rounded-2xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform"><Settings className="w-7 h-7" /></div>
        <h3 className="font-bold text-gray-800 text-sm">ระบบตั้งค่า</h3><p className="text-[11px] text-gray-400 mt-1">Super Admin</p>
      </Link>
    </div>
  </motion.div>
);

export default function App() {
  const [profile, setProfile] = useState(null);
  const [error, setError] = useState('');
  const location = useLocation();
  const navigate = useNavigate();

  const queryParams = new URLSearchParams(location.search);
  const companyKey = queryParams.get('company') || 'pro_nexus';
  const targetPath = queryParams.get('path');
  const activeLiffId = COMPANY_LIFF_IDS[companyKey] || COMPANY_LIFF_IDS['pro_nexus'];

  useEffect(() => {
    liff.init({ liffId: activeLiffId })
      .then(() => {
        if (!liff.isLoggedIn()) {
          liff.login();
        } else {
          liff.getProfile().then(userProfile => {
            setProfile(userProfile);
            
            // 🚀 [เพิ่มใหม่] ส่งข้อมูลไปหา Backend FastAPI เพื่ออัปเดตสิทธิ์และ Rich Menu
            fetch(`${BACKEND_URL}/api/v1/${companyKey}/sync-user`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                userId: userProfile.userId,
                displayName: userProfile.displayName,
                pictureUrl: userProfile.pictureUrl
              })
            }).catch(err => console.log("Backend Sync Error:", err)); // แอบทำเงียบๆ หลังบ้าน

            // Redirect ตาม Path ของ Rich Menu
            if (targetPath) {
              navigate(targetPath, { replace: true });
            }
          }).catch(err => setError(err.message));
        }
      })
      .catch(err => setError("LIFF Error: " + err.message));
  }, [activeLiffId, targetPath, navigate, companyKey]);

  return (
    <div className="min-h-screen bg-slate-50 font-sans flex justify-center selection:bg-indigo-100">
      <div className="w-full max-w-md bg-slate-50 min-h-screen flex flex-col relative overflow-hidden">
        <div className="absolute top-[-10%] left-[-10%] w-64 h-64 bg-indigo-300 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-blob"></div>
        <div className="absolute top-[-10%] right-[-10%] w-64 h-64 bg-emerald-300 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-blob animation-delay-2000"></div>
        
        <header className="px-6 pt-10 pb-4 relative z-10 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 bg-gray-900 rounded-xl flex items-center justify-center"><Zap className="w-4 h-4 text-white" /></div>
            <h1 className="text-xl font-extrabold tracking-tight text-gray-900">Nexus OS</h1>
          </div>
          <span className="bg-white/60 backdrop-blur-md text-[10px] px-3 py-1.5 rounded-full uppercase font-bold text-indigo-600 shadow-sm border border-indigo-50">
            {companyKey.replace('_', ' ')}
          </span>
        </header>
        
        {error && <div className="mx-6 p-3 bg-red-50 text-red-600 rounded-xl border border-red-100 text-xs text-center z-10">{error}</div>}
        
        <main className="flex-grow z-10 relative">
          <Routes>
            <Route path="/" element={<Home profile={profile} companyKey={companyKey} />} />
            <Route path="/team" element={<TeamUI />} />
            <Route path="/shop" element={<ShopUI />} />
            <Route path="/qrcode" element={<QrCodeUI />} />
            <Route path="/admin" element={<SuperAdminUI />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}
