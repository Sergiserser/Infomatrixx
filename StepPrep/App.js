import React, { useState, useEffect, useRef } from 'react';
import {
  View, Text, ScrollView, TouchableOpacity, TextInput,
  StyleSheet, SafeAreaView, StatusBar, Alert, Animated,
  Modal, KeyboardAvoidingView, Platform, Dimensions,
  FlatList, Pressable, Image,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

const { width: W, height: H } = Dimensions.get('window');

// ── Themes (exact from SafeReady-Complete.tsx) ──────────────────
const THEMES = {
  modern:  { name:'Modern',  primary:'#1a1a1a', accent:'#3b82f6', danger:'#ef4444', success:'#10b981', warning:'#f59e0b', bg:'#ffffff', bg2:'#f9fafb', border:'#e5e7eb', text:'#111827', text2:'#6b7280' },
  bold:    { name:'Bold',    primary:'#dc2626', accent:'#ea580c', danger:'#b91c1c', success:'#16a34a', warning:'#d97706', bg:'#fef2f2', bg2:'#fee2e2', border:'#fca5a5', text:'#450a0a', text2:'#991b1b' },
  calm:    { name:'Calm',    primary:'#0891b2', accent:'#06b6d4', danger:'#f43f5e', success:'#14b8a6', warning:'#f59e0b', bg:'#f0fdfa', bg2:'#ccfbf1', border:'#5eead4', text:'#134e4a', text2:'#0f766e' },
  vibrant: { name:'Vibrant', primary:'#8b5cf6', accent:'#ec4899', danger:'#f43f5e', success:'#22c55e', warning:'#fbbf24', bg:'#faf5ff', bg2:'#f3e8ff', border:'#d8b4fe', text:'#581c87', text2:'#7c3aed' },
};

// ── Default data (from SafeReady-Complete.tsx) ───────────────────
const DEFAULT = {
  tasks: [
    { id:'1', text:'Check water supply',       done:true  },
    { id:'2', text:'Test emergency radio',      done:true  },
    { id:'3', text:'Rotate food stock',         done:false },
    { id:'4', text:'Share plan with family',    done:false },
  ],
  supplies: [
    { id:'1', name:'Bottled water',      qty:'12 L · expires Aug 2026', status:'ok',      cat:'water-food' },
    { id:'2', name:'Emergency rations',  qty:'3 days · expires Mar 2026',status:'expired', cat:'water-food' },
    { id:'3', name:'First aid kit',      qty:'Complete set',             status:'ok',      cat:'medical'    },
    { id:'4', name:'Prescription meds', qty:'Not added yet',            status:'missing', cat:'medical'    },
    { id:'5', name:'Flashlight + batteries', qty:'2 units',             status:'ok',      cat:'tools'      },
  ],
  contacts: [
    { id:'1', name:'Maria A.', role:'Primary · Mom',    phone:'+40 123 456 789', initials:'MA', primary:true  },
    { id:'2', name:'Dan P.',   role:'Neighbor',          phone:'+40 234 567 890', initials:'DP', primary:false },
  ],
  plans: [
    { id:'1', icon:'map',   title:'Route A — Primary exit',  sub:'Via main street → shelter',      type:'route'   },
    { id:'2', icon:'pin',   title:'Meeting point',           sub:'City park — main fountain',      type:'route'   },
    { id:'3', icon:'flame', title:'Fire',                    sub:'Floor plan + 2 exits mapped',    type:'disaster'},
    { id:'4', icon:'wave',  title:'Flood',                   sub:'High-ground route selected',     type:'disaster'},
    { id:'5', icon:'bolt',  title:'Earthquake',              sub:'Shelter-in-place protocol set',  type:'disaster'},
  ],
  theme:  'modern',
  shelter: '',
  api_token:  '', api_region:  '', api_alerts: [],
  gemini_key: '', gemini_region: '',
  showAlert: true,
};

const SAVE_KEY = 'stepprep_v1';

// ── Helper to hex with alpha ──────────────────────────────────────
function alpha(hex, a) {
  const r = parseInt(hex.slice(1,3),16);
  const g = parseInt(hex.slice(3,5),16);
  const b = parseInt(hex.slice(5,7),16);
  return `rgba(${r},${g},${b},${a})`;
}

// ══════════════════════════════════════════════════════════════════
//  REUSABLE COMPONENTS
// ══════════════════════════════════════════════════════════════════

function Card({ children, style, t }) {
  return (
    <View style={[{ backgroundColor:t.bg, borderRadius:12, borderWidth:1, borderColor:t.border, padding:14, marginBottom:10, shadowColor:'#000', shadowOpacity:.06, shadowRadius:4, shadowOffset:{width:0,height:2}, elevation:2 }, style]}>
      {children}
    </View>
  );
}

function SectionHeader({ title, action, actionLabel, t }) {
  return (
    <View style={{ flexDirection:'row', justifyContent:'space-between', alignItems:'center', marginBottom:12, marginTop:8 }}>
      <Text style={{ fontSize:14, fontWeight:'600', color:t.text }}>{title}</Text>
      {action && <TouchableOpacity onPress={action}><Text style={{ fontSize:12, color:t.accent, fontWeight:'500' }}>{actionLabel}</Text></TouchableOpacity>}
    </View>
  );
}

function Badge({ status, t }) {
  const cfg = {
    ok:      { bg: alpha(t.success,.12), color: t.success, label:'OK'      },
    expired: { bg: alpha(t.warning,.12), color: t.warning, label:'Expired' },
    low:     { bg: alpha(t.warning,.12), color: t.warning, label:'Low'     },
    missing: { bg: alpha(t.danger, .12), color: t.danger,  label:'Missing' },
  };
  const c = cfg[status] || cfg.ok;
  return (
    <View style={{ backgroundColor:c.bg, paddingHorizontal:8, paddingVertical:3, borderRadius:20 }}>
      <Text style={{ fontSize:11, fontWeight:'600', color:c.color }}>{c.label}</Text>
    </View>
  );
}

function Avatar({ initials, primary, t }) {
  return (
    <View style={{ width:40, height:40, borderRadius:20, backgroundColor: alpha(primary ? t.success : t.accent, .15), alignItems:'center', justifyContent:'center' }}>
      <Text style={{ fontSize:14, fontWeight:'700', color: primary ? t.success : t.accent }}>{initials}</Text>
    </View>
  );
}

function PrimaryButton({ label, onPress, t, style }) {
  return (
    <TouchableOpacity onPress={onPress} style={[{ backgroundColor:t.accent, borderRadius:10, paddingVertical:13, alignItems:'center' }, style]}>
      <Text style={{ color:'#fff', fontWeight:'700', fontSize:15 }}>{label}</Text>
    </TouchableOpacity>
  );
}

function GhostButton({ label, onPress, t, style }) {
  return (
    <TouchableOpacity onPress={onPress} style={[{ backgroundColor:t.bg2, borderRadius:10, paddingVertical:13, alignItems:'center', borderWidth:1, borderColor:t.border }, style]}>
      <Text style={{ color:t.text2, fontWeight:'600', fontSize:15 }}>{label}</Text>
    </TouchableOpacity>
  );
}

// ── Input Modal (web-compatible overlay) ─────────────────────────
function InputModal({ visible, title, fields, onSubmit, onCancel, t }) {
  const [vals, setVals] = useState({});
  useEffect(() => { if (visible) setVals({}) }, [visible]);
  if (!visible) return null;
  return (
    <View style={{ position:'absolute', top:0, left:0, right:0, bottom:0,
      backgroundColor:'rgba(0,0,0,0.5)', justifyContent:'flex-end',
      zIndex:999 }}>
      <TouchableOpacity style={{ flex:1 }} onPress={onCancel} activeOpacity={1} />
      <View style={{ backgroundColor:t.bg, borderTopLeftRadius:20, borderTopRightRadius:20,
        padding:20, borderTopWidth:1, borderColor:t.border }}>
        <View style={{ width:36, height:4, backgroundColor:t.border, borderRadius:2,
          alignSelf:'center', marginBottom:16 }} />
        <Text style={{ fontSize:18, fontWeight:'700', color:t.text,
          textAlign:'center', marginBottom:18 }}>{title}</Text>
        {fields.map(f => (
          <View key={f.id} style={{ marginBottom:12 }}>
            <Text style={{ fontSize:12, color:t.text2, fontWeight:'500', marginBottom:5 }}>{f.label}</Text>
            <TextInput
              placeholder={f.placeholder}
              placeholderTextColor={t.text2}
              value={vals[f.id]||''}
              onChangeText={v => setVals(prev => ({...prev, [f.id]:v}))}
              secureTextEntry={f.secure||false}
              autoFocus={false}
              style={{ borderWidth:1.5, borderColor:t.border, borderRadius:8,
                padding:11, fontSize:14, color:t.text, backgroundColor:t.bg2 }}
            />
          </View>
        ))}
        <View style={{ flexDirection:'row', gap:10, marginTop:8 }}>
          <GhostButton label="Cancel" onPress={onCancel} t={t} style={{ flex:1 }} />
          <PrimaryButton label="Save" onPress={() => { onSubmit(vals); }} t={t} style={{ flex:1 }} />
        </View>
      </View>
    </View>
  );
}

// ── Confirm Modal (web-compatible) ────────────────────────────────
function ConfirmModal({ visible, message, onConfirm, onCancel, t }) {
  if (!visible) return null;
  return (
    <View style={{ position:'absolute', top:0, left:0, right:0, bottom:0,
      backgroundColor:'rgba(0,0,0,0.5)', justifyContent:'center',
      alignItems:'center', padding:24, zIndex:999 }}>
      <View style={{ backgroundColor:t.bg, borderRadius:16, padding:24,
        width:'100%', maxWidth:300, borderWidth:1, borderColor:t.border }}>
        <Text style={{ fontSize:16, fontWeight:'700', color:t.text,
          textAlign:'center', marginBottom:6 }}>{message}</Text>
        <Text style={{ fontSize:13, color:t.text2,
          textAlign:'center', marginBottom:20 }}>This cannot be undone.</Text>
        <View style={{ flexDirection:'row', gap:10 }}>
          <GhostButton label="Cancel" onPress={onCancel} t={t} style={{ flex:1 }} />
          <TouchableOpacity onPress={onConfirm}
            style={{ flex:1, backgroundColor:t.danger, borderRadius:10,
              paddingVertical:13, alignItems:'center' }}>
            <Text style={{ color:'#fff', fontWeight:'700', fontSize:15 }}>Delete</Text>
          </TouchableOpacity>
        </View>
      </View>
    </View>
  );
}

// ══════════════════════════════════════════════════════════════════
//  SCREENS
// ══════════════════════════════════════════════════════════════════

// ── HOME ─────────────────────────────────────────────────────────
function HomeScreen({ data, setData, t }) {
  const [modal, setModal] = useState(false);
  const [confirm, setConfirm] = useState(null);

  const ok   = data.supplies.filter(s => s.status==='ok').length;
  const tot  = data.supplies.length;
  const done = data.tasks.filter(t => t.done).length;

  const quickCards = [
    { label:'Supply kit',  val:`${ok}/${tot} stocked`,        color:t.success },
    { label:'Contacts',    val:`${data.contacts.length} people`, color:t.accent  },
    { label:'Tasks done',  val:`${done}/${data.tasks.length}`, color:t.warning  },
    { label:'Plans ready', val:data.plans.length ? 'Set' : 'Not set', color:t.danger  },
  ];

  function toggleTask(id) {
    setData(d => ({...d, tasks: d.tasks.map(t => t.id===id ? {...t,done:!t.done} : t)}));
  }

  function addTask(vals) {
    if (!vals || !vals.f0 || !vals.f0.trim()) return;
    setData(d => ({...d, tasks:[...d.tasks,{id:Date.now()+'',text:vals.f0.trim(),done:false}]}));
    setModal(false);
  }

  function delTask(id) {
    setData(d => ({...d, tasks:d.tasks.filter(t=>t.id!==id)}));
    setConfirm(null);
  }

  return (
    <View style={{ flex:1 }}>
    <ScrollView style={{ flex:1, backgroundColor:t.bg }} contentContainerStyle={{ padding:16, paddingBottom:20 }} showsVerticalScrollIndicator={false}>

      {/* Alert banner */}
      {data.showAlert && (
        <View style={{ backgroundColor:alpha(t.warning,.1), borderWidth:1, borderColor:alpha(t.warning,.4), borderRadius:10, padding:12, flexDirection:'row', gap:10, marginBottom:16 }}>
          <Text style={{ fontSize:18 }}>⚠️</Text>
          <View style={{ flex:1 }}>
            <Text style={{ fontSize:13, fontWeight:'600', color:t.text }}>Severe storm warning</Text>
            <Text style={{ fontSize:11, color:t.text2, marginTop:2 }}>Active until 11 PM · Tap for details</Text>
          </View>
          <TouchableOpacity onPress={() => setData(d=>({...d,showAlert:false}))}>
            <Text style={{ fontSize:18, color:t.text2 }}>×</Text>
          </TouchableOpacity>
        </View>
      )}

      {/* Readiness */}
      <SectionHeader title="Your readiness" t={t} />
      <View style={{ flexDirection:'row', flexWrap:'wrap', gap:8, marginBottom:20 }}>
        {quickCards.map((c,i) => (
          <View key={i} style={{ width:(W-48)/2, backgroundColor:t.bg2, borderRadius:10, padding:12, borderWidth:1, borderColor:t.border }}>
            <View style={{ width:32, height:32, borderRadius:16, backgroundColor:alpha(c.color,.15), alignItems:'center', justifyContent:'center', marginBottom:8 }}>
              <Text style={{ fontSize:16 }}>{['📦','📞','✅','🗺️'][i]}</Text>
            </View>
            <Text style={{ fontSize:12, fontWeight:'500', color:t.text }}>{c.label}</Text>
            <Text style={{ fontSize:11, color:t.text2, marginTop:2 }}>{c.val}</Text>
          </View>
        ))}
      </View>

      {/* Shelter */}
      <TouchableOpacity style={{ backgroundColor:t.bg2, borderRadius:10, padding:12, flexDirection:'row', alignItems:'center', gap:10, marginBottom:16, borderWidth:1, borderColor:t.border }}>
        <Text style={{ fontSize:18 }}>🏠</Text>
        <Text style={{ fontSize:14, color:data.shelter?t.text:t.text2 }}>{data.shelter || 'Tap to set shelter location'}</Text>
      </TouchableOpacity>

      {/* Tasks */}
      <SectionHeader title="Today's tasks" action={() => setModal(true)} actionLabel="+ Add" t={t} />
      {data.tasks.length === 0 && <Text style={{ color:t.text2, fontSize:14, textAlign:'center', paddingVertical:20 }}>No tasks — tap + Add</Text>}
      {data.tasks.map(task => (
        <TouchableOpacity key={task.id} onPress={() => toggleTask(task.id)} style={{ flexDirection:'row', alignItems:'center', gap:12, paddingVertical:10, borderBottomWidth:1, borderColor:t.border }}>
          <View style={{ width:20, height:20, borderRadius:5, borderWidth:2, borderColor:task.done?t.success:t.border, backgroundColor:task.done?t.success:'transparent', alignItems:'center', justifyContent:'center' }}>
            {task.done && <Text style={{ color:'#fff', fontSize:12, fontWeight:'700' }}>✓</Text>}
          </View>
          <Text style={{ flex:1, fontSize:14, color:t.text, textDecorationLine:task.done?'line-through':'none', opacity:task.done?.5:1 }}>{task.text}</Text>
          <TouchableOpacity onPress={() => setConfirm({msg:'Delete task?', cb:()=>delTask(task.id)})}>
            <Text style={{ color:t.text2, fontSize:18, opacity:.4 }}>×</Text>
          </TouchableOpacity>
        </TouchableOpacity>
      ))}

    </ScrollView>
    <InputModal visible={modal} title="New Task" fields={[{id:'f0',label:'Description',placeholder:'e.g. Check water supply'}]} onSubmit={addTask} onCancel={()=>setModal(false)} t={t} />
    {confirm && <ConfirmModal visible message={confirm.msg} onConfirm={confirm.cb} onCancel={()=>setConfirm(null)} t={t} />}
    </View>
  );
}

// ── KIT ──────────────────────────────────────────────────────────
function KitScreen({ data, setData, t }) {
  const [modal, setModal]   = useState(false);
  const [confirm, setConfirm] = useState(null);

  const cats = [
    { key:'water-food', label:'Water & Food' },
    { key:'medical',    label:'Medical'       },
    { key:'tools',      label:'Tools'         },
  ];

  function cycleStatus(id) {
    const cycle = ['ok','low','missing','expired'];
    setData(d => ({...d, supplies: d.supplies.map(s => s.id===id ? {...s, status:cycle[(cycle.indexOf(s.status)+1)%cycle.length]} : s)}));
  }

  function addSupply(vals) {
    if (!vals || !vals.f0 || !vals.f0.trim()) return;
    setData(d => ({...d, supplies:[...d.supplies,{id:Date.now()+'',name:vals.f0.trim(),qty:(vals.f1||'').trim(),status:'ok',cat:(vals.f2||'').trim()||'tools'}]}));
    setModal(false);
  }

  function delSupply(id) {
    setData(d => ({...d, supplies:d.supplies.filter(s=>s.id!==id)}));
    setConfirm(null);
  }

  const ok  = data.supplies.filter(s=>s.status==='ok').length;
  const pct = data.supplies.length ? Math.round(ok/data.supplies.length*100) : 0;

  return (
    <View style={{ flex:1 }}>
    <ScrollView style={{ flex:1, backgroundColor:t.bg }} contentContainerStyle={{ padding:16, paddingBottom:20 }} showsVerticalScrollIndicator={false}>
      <SectionHeader title="Supply Kit" action={()=>setModal(true)} actionLabel="+ Add" t={t} />

      {/* Readiness bar */}
      <Card t={t} style={{ marginBottom:16 }}>
        <View style={{ flexDirection:'row', justifyContent:'space-between', marginBottom:8 }}>
          <Text style={{ fontSize:12, fontWeight:'500', color:t.text2 }}>Overall readiness</Text>
          <Text style={{ fontSize:16, fontWeight:'700', color:pct>=70?t.success:pct>=40?t.warning:t.danger }}>{pct}%</Text>
        </View>
        <View style={{ height:8, backgroundColor:t.bg2, borderRadius:4, overflow:'hidden' }}>
          <View style={{ height:'100%', width:`${pct}%`, backgroundColor:pct>=70?t.success:pct>=40?t.warning:t.danger, borderRadius:4 }} />
        </View>
      </Card>

      {cats.map(cat => {
        const items = data.supplies.filter(s=>s.cat===cat.key);
        if (!items.length) return null;
        return (
          <View key={cat.key} style={{ marginBottom:16 }}>
            <Text style={{ fontSize:12, fontWeight:'600', color:t.text2, textTransform:'uppercase', letterSpacing:.5, marginBottom:8 }}>{cat.label}</Text>
            <Card t={t} style={{ padding:0, paddingHorizontal:14 }}>
              {items.map((s, i) => (
                <View key={s.id} style={{ flexDirection:'row', alignItems:'center', paddingVertical:12, borderBottomWidth:i<items.length-1?1:0, borderColor:t.border, gap:12 }}>
                  <View style={{ width:32, height:32, borderRadius:8, backgroundColor:alpha(t.accent,.12), alignItems:'center', justifyContent:'center' }}>
                    <Text style={{ fontSize:15 }}>{'💧📦💊⚡'[['water-food','water-food','medical','tools'].indexOf(cat.key)]||'📦'}</Text>
                  </View>
                  <View style={{ flex:1 }}>
                    <Text style={{ fontSize:13, fontWeight:'500', color:t.text }}>{s.name}</Text>
                    <Text style={{ fontSize:11, color:t.text2, marginTop:2 }}>{s.qty}</Text>
                  </View>
                  <TouchableOpacity onPress={()=>cycleStatus(s.id)}>
                    <Badge status={s.status} t={t} />
                  </TouchableOpacity>
                  <TouchableOpacity onPress={()=>setConfirm({msg:'Delete supply?',cb:()=>delSupply(s.id)})}>
                    <Text style={{ color:t.text2, fontSize:18, opacity:.4 }}>×</Text>
                  </TouchableOpacity>
                </View>
              ))}
            </Card>
          </View>
        );
      })}

      {!data.supplies.length && <Text style={{ color:t.text2, fontSize:14, textAlign:'center', paddingVertical:30 }}>Kit is empty — tap + Add to start</Text>}

    </ScrollView>
    <InputModal visible={modal} title="Add Supply" fields={[
      {id:'f0',label:'Item name',placeholder:'e.g. Bottled water'},
      {id:'f1',label:'Quantity',placeholder:'e.g. 12 L'},
      {id:'f2',label:'Category',placeholder:'water-food / medical / tools'},
    ]} onSubmit={addSupply} onCancel={()=>setModal(false)} t={t} />
    {confirm && <ConfirmModal visible message={confirm.msg} onConfirm={confirm.cb} onCancel={()=>setConfirm(null)} t={t} />}
    </View>
  );
}

// ── SOS ──────────────────────────────────────────────────────────
function SOSScreen({ data, setData, t }) {
  const [status, setStatus] = useState('Hold button for 3 seconds to activate');
  const [statusColor, setStatusColor] = useState(null);
  const [modal, setModal] = useState(false);
  const [confirm, setConfirm] = useState(null);
  const timerRef = useRef(null);
  const progRef  = useRef(0);
  const scaleAnim = useRef(new Animated.Value(1)).current;

  function startSOS() {
    progRef.current = 0;
    Animated.loop(Animated.sequence([
      Animated.timing(scaleAnim,{toValue:1.06,duration:400,useNativeDriver:true}),
      Animated.timing(scaleAnim,{toValue:1,duration:400,useNativeDriver:true}),
    ])).start();
    timerRef.current = setInterval(() => {
      progRef.current += 100;
      const pct = Math.min(100, Math.round(progRef.current / 3000 * 100));
      setStatus(`Activating… ${pct}%`);
      setStatusColor(t.danger);
      if (progRef.current >= 3000) {
        clearInterval(timerRef.current);
        setStatus('🚨 SOS ACTIVATED — alerting contacts');
        scaleAnim.stopAnimation();
        scaleAnim.setValue(1);
      }
    }, 100);
  }

  function cancelSOS() {
    if (timerRef.current) clearInterval(timerRef.current);
    scaleAnim.stopAnimation(); scaleAnim.setValue(1);
    if (progRef.current < 3000) { setStatus('Hold button for 3 seconds to activate'); setStatusColor(null); }
    progRef.current = 0;
  }

  function addContact(vals) {
    if (!vals || !vals.f0 || !vals.f0.trim()) return;
    const name = vals.f0.trim();
    setData(d => ({...d, contacts:[...d.contacts,{id:Date.now()+'',name,phone:(vals.f1||'').trim(),role:(vals.f2||'').trim(),initials:name.split(' ').map(x=>x[0]).join('').toUpperCase().slice(0,2)||'?',primary:false}]}));
    setModal(false);
  }

  function delContact(id) {
    setData(d => ({...d, contacts:d.contacts.filter(c=>c.id!==id)}));
    setConfirm(null);
  }

  return (
    <View style={{ flex:1 }}>
    <ScrollView style={{ flex:1, backgroundColor:t.bg }} contentContainerStyle={{ padding:16, paddingBottom:20 }} showsVerticalScrollIndicator={false}>

      {/* SOS Button */}
      <View style={{ alignItems:'center', paddingVertical:28 }}>
        <Animated.View style={{ transform:[{scale:scaleAnim}] }}>
          <Pressable onPressIn={startSOS} onPressOut={cancelSOS}
            style={{ width:160, height:160, borderRadius:80, backgroundColor:t.danger, alignItems:'center', justifyContent:'center',
              shadowColor:t.danger, shadowOpacity:.5, shadowRadius:20, shadowOffset:{width:0,height:8}, elevation:12 }}>
            <Text style={{ fontSize:46, fontWeight:'800', color:'#fff', letterSpacing:2 }}>SOS</Text>
            <Text style={{ fontSize:10, color:'rgba(255,255,255,.7)', marginTop:4 }}>HOLD 3 SEC</Text>
          </Pressable>
        </Animated.View>
      </View>

      <Text style={{ textAlign:'center', fontSize:13, color:statusColor||t.text2, marginBottom:16, fontWeight:statusColor?'600':'400' }}>{status}</Text>

      {/* National */}
      <View style={{ backgroundColor:alpha(t.danger,.08), borderWidth:1, borderColor:alpha(t.danger,.2), borderRadius:10, padding:12, marginBottom:16 }}>
        <Text style={{ fontSize:13, fontWeight:'600', color:t.danger, marginBottom:4 }}>National emergency</Text>
        <Text style={{ fontSize:12, color:t.text2 }}>Call 112 · Fire: 101 · Police: 102 · Ambulance: 103</Text>
      </View>

      {/* Will send */}
      <Card t={t} style={{ marginBottom:16 }}>
        <Text style={{ fontSize:13, fontWeight:'600', color:t.text, marginBottom:6 }}>Will send to all contacts:</Text>
        <Text style={{ fontSize:13, color:t.text2, marginBottom:4 }}>• Your GPS location</Text>
        <Text style={{ fontSize:13, color:t.text2 }}>• Emergency alert message</Text>
      </Card>

      {/* Contacts */}
      <SectionHeader title="Emergency contacts" action={()=>setModal(true)} actionLabel="+ Add" t={t} />
      {data.contacts.length === 0 && <Text style={{ color:t.text2, fontSize:14, textAlign:'center', paddingVertical:16 }}>No contacts — tap + Add</Text>}
      {data.contacts.map(c => (
        <View key={c.id} style={{ flexDirection:'row', alignItems:'center', gap:12, paddingVertical:10, borderBottomWidth:1, borderColor:t.border }}>
          <Avatar initials={c.initials} primary={c.primary} t={t} />
          <View style={{ flex:1 }}>
            <Text style={{ fontSize:14, fontWeight:'600', color:t.text }}>{c.name}</Text>
            <Text style={{ fontSize:12, color:t.text2 }}>{c.phone}</Text>
            <Text style={{ fontSize:11, color:t.text2, opacity:.6 }}>{c.role}</Text>
          </View>
          <Text style={{ fontSize:22, color:t.success }}>📞</Text>
          <TouchableOpacity onPress={()=>setConfirm({msg:'Delete contact?',cb:()=>delContact(c.id)})}>
            <Text style={{ color:t.text2, fontSize:18, opacity:.4 }}>×</Text>
          </TouchableOpacity>
        </View>
      ))}

    </ScrollView>
    <InputModal visible={modal} title="New Contact" fields={[
      {id:'f0',label:'Name',placeholder:'Full name'},
      {id:'f1',label:'Phone',placeholder:'+1 555 000 0000'},
      {id:'f2',label:'Role',placeholder:'e.g. Family, Neighbour'},
    ]} onSubmit={addContact} onCancel={()=>setModal(false)} t={t} />
    {confirm && <ConfirmModal visible message={confirm.msg} onConfirm={confirm.cb} onCancel={()=>setConfirm(null)} t={t} />}
    </View>
  );
}

// ── PLAN ─────────────────────────────────────────────────────────
function PlanScreen({ data, setData, t }) {
  const icons = { map:'🗺️', pin:'📍', flame:'🔥', wave:'🌊', bolt:'⚡' };
  const iconColors = { map:t.accent, pin:t.success, flame:t.danger, wave:t.accent, bolt:t.warning };

  const routes    = data.plans.filter(p=>p.type==='route');
  const disasters = data.plans.filter(p=>p.type==='disaster');

  return (
    <ScrollView style={{ flex:1, backgroundColor:t.bg }} contentContainerStyle={{ padding:16, paddingBottom:20 }} showsVerticalScrollIndicator={false}>
      <SectionHeader title="Evacuation Plan" t={t} />

      {routes.length>0 && <>
        <Text style={{ fontSize:12, fontWeight:'600', color:t.text2, textTransform:'uppercase', letterSpacing:.5, marginBottom:8 }}>Routes</Text>
        {routes.map(p=>(
          <View key={p.id} style={{ flexDirection:'row', alignItems:'center', gap:12, backgroundColor:t.bg2, borderRadius:10, padding:12, marginBottom:8, borderWidth:1, borderColor:t.border }}>
            <View style={{ width:36, height:36, borderRadius:8, backgroundColor:alpha(iconColors[p.icon]||t.accent,.15), alignItems:'center', justifyContent:'center' }}>
              <Text style={{ fontSize:18 }}>{icons[p.icon]||'🗺️'}</Text>
            </View>
            <View style={{ flex:1 }}>
              <Text style={{ fontSize:13, fontWeight:'600', color:t.text }}>{p.title}</Text>
              <Text style={{ fontSize:11, color:t.text2, marginTop:2 }}>{p.sub}</Text>
            </View>
            <Text style={{ color:t.text2, fontSize:18 }}>›</Text>
          </View>
        ))}
      </>}

      {disasters.length>0 && <>
        <Text style={{ fontSize:12, fontWeight:'600', color:t.text2, textTransform:'uppercase', letterSpacing:.5, marginBottom:8, marginTop:8 }}>Plan for each disaster</Text>
        {disasters.map(p=>(
          <View key={p.id} style={{ flexDirection:'row', alignItems:'center', gap:12, backgroundColor:t.bg2, borderRadius:10, padding:12, marginBottom:8, borderWidth:1, borderColor:t.border }}>
            <View style={{ width:36, height:36, borderRadius:8, backgroundColor:alpha(iconColors[p.icon]||t.accent,.15), alignItems:'center', justifyContent:'center' }}>
              <Text style={{ fontSize:18 }}>{icons[p.icon]||'⚠️'}</Text>
            </View>
            <View style={{ flex:1 }}>
              <Text style={{ fontSize:13, fontWeight:'600', color:t.text }}>{p.title}</Text>
              <Text style={{ fontSize:11, color:t.text2, marginTop:2 }}>{p.sub}</Text>
            </View>
            <Text style={{ color:t.text2, fontSize:18 }}>›</Text>
          </View>
        ))}
      </>}
    </ScrollView>
  );
}

// ── SETTINGS ─────────────────────────────────────────────────────
function SettingsScreen({ data, setData, themeName, setThemeName, t }) {
  const Row = ({ label, right }) => (
    <View style={{ flexDirection:'row', justifyContent:'space-between', alignItems:'center', paddingVertical:14, borderBottomWidth:1, borderColor:t.border }}>
      <Text style={{ fontSize:14, fontWeight:'500', color:t.text }}>{label}</Text>
      {right}
    </View>
  );

  return (
    <ScrollView style={{ flex:1, backgroundColor:t.bg }} contentContainerStyle={{ padding:16, paddingBottom:40 }}>
      <Text style={{ fontSize:18, fontWeight:'700', color:t.text, marginBottom:16 }}>Settings</Text>

      <Text style={{ fontSize:12, fontWeight:'600', color:t.text2, textTransform:'uppercase', letterSpacing:.5, marginBottom:10 }}>Theme</Text>
      <View style={{ flexDirection:'row', flexWrap:'wrap', gap:8, marginBottom:20 }}>
        {Object.entries(THEMES).map(([key,th]) => (
          <TouchableOpacity key={key} onPress={()=>setThemeName(key)}
            style={{ paddingHorizontal:14, paddingVertical:8, borderRadius:8, backgroundColor:th.bg2,
              borderWidth:2, borderColor:themeName===key?th.accent:th.border }}>
            <Text style={{ fontSize:13, fontWeight:'600', color:th.text }}>{th.name}</Text>
          </TouchableOpacity>
        ))}
      </View>

      <Row label="App name" right={<Text style={{ fontSize:13, color:t.text2 }}>StepPrep</Text>} />
      <Row label="Tasks" right={<Text style={{ fontSize:13, color:t.text2 }}>{data.tasks.length}</Text>} />
      <Row label="Supplies" right={<Text style={{ fontSize:13, color:t.text2 }}>{data.supplies.length}</Text>} />
      <Row label="Contacts" right={<Text style={{ fontSize:13, color:t.text2 }}>{data.contacts.length}</Text>} />

      <TouchableOpacity style={{ marginTop:24 }} onPress={() => Alert.alert('Clear all data?','This cannot be undone.',[{text:'Cancel'},{text:'Clear',style:'destructive',onPress:()=>setData({...DEFAULT})}])}>
        <Text style={{ color:t.danger, fontSize:14 }}>Clear all data</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

// ── AI SCOUT ─────────────────────────────────────────────────────
function AIScreen({ data, setData, t }) {
  const [key, setKey]       = useState(data.gemini_key || '');
  const [region, setRegion] = useState(data.gemini_region || '');
  const [loading, setLoading] = useState(false);
  const [result, setResult]   = useState(null);
  const [saved, setSaved]     = useState(!!data.gemini_key);

  async function scan() {
    if (!key.trim() || !region.trim()) {
      Alert.alert('Missing info', 'Enter both API key and region first.');
      return;
    }
    setLoading(true); setResult(null);
    try {
      const prompt = `You are a disaster preparedness expert. For the region "${region}", return ONLY a JSON object with "kit" (array of 8-12 supply item strings) and "tasks" (array of 6-10 task strings). No explanation, just JSON.`;
      const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${key.trim()}`;
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ contents: [{ parts: [{ text: prompt }] }] }),
      });
      const json = await res.json();
      if (json.error) throw new Error(json.error.message);
      let text = json.candidates[0].content.parts[0].text.trim();
      if (text.includes('```')) text = text.split('```')[1].replace(/^json/, '').trim();
      const parsed = JSON.parse(text);
      // Add to data
      const newKit   = (parsed.kit   || []).filter(x => typeof x === 'string' && x.trim());
      const newTasks = (parsed.tasks || []).filter(x => typeof x === 'string' && x.trim());
      setData(d => ({
        ...d,
        gemini_key: key.trim(), gemini_region: region.trim(),
        supplies: [...d.supplies, ...newKit.map((name,i)   => ({ id: Date.now()+i+'k', name: name.trim(), qty:'', status:'ok', cat:'tools' }))],
        tasks:    [...d.tasks,    ...newTasks.map((text,i)  => ({ id: Date.now()+i+'t', text: text.trim(), done: false }))],
      }));
      setResult({ kit: newKit, tasks: newTasks });
      setSaved(true);
    } catch(e) {
      Alert.alert('Error', e.message || 'Could not reach Gemini. Check your API key.');
    }
    setLoading(false);
  }

  return (
    <ScrollView style={{ flex:1, backgroundColor:t.bg }} contentContainerStyle={{ padding:16, paddingBottom:30 }} showsVerticalScrollIndicator={false}>
      <Text style={{ fontSize:19, fontWeight:'700', color:t.text, marginBottom:4 }}>AI Hazard Scout</Text>
      <Text style={{ fontSize:13, color:t.text2, marginBottom:20 }}>Gemini detects hazards for your region and auto-fills your Kit & Tasks.</Text>

      {/* API Key */}
      <Text style={{ fontSize:12, fontWeight:'600', color:t.text2, marginBottom:6, textTransform:'uppercase', letterSpacing:.5 }}>Gemini API Key</Text>
      <TextInput
        value={key}
        onChangeText={setKey}
        placeholder="AIza... (get free at aistudio.google.com)"
        placeholderTextColor={t.text2}
        secureTextEntry
        style={{ borderWidth:1.5, borderColor:t.border, borderRadius:10, padding:12, fontSize:14, color:t.text, backgroundColor:t.bg2, marginBottom:14 }}
      />

      {/* Region */}
      <Text style={{ fontSize:12, fontWeight:'600', color:t.text2, marginBottom:6, textTransform:'uppercase', letterSpacing:.5 }}>Your Region</Text>
      <TextInput
        value={region}
        onChangeText={setRegion}
        placeholder="e.g. Kyiv, California, Tokyo..."
        placeholderTextColor={t.text2}
        style={{ borderWidth:1.5, borderColor:t.border, borderRadius:10, padding:12, fontSize:14, color:t.text, backgroundColor:t.bg2, marginBottom:16 }}
      />

      <TouchableOpacity onPress={scan} disabled={loading}
        style={{ backgroundColor: loading ? t.text2 : t.accent, borderRadius:10, paddingVertical:14, alignItems:'center', marginBottom:20 }}>
        <Text style={{ color:'#fff', fontWeight:'700', fontSize:15 }}>{loading ? 'Scanning...' : '🔍  Scan My Region'}</Text>
      </TouchableOpacity>

      {result && (
        <View>
          <View style={{ backgroundColor:alpha(t.success,.1), borderRadius:10, padding:14, borderWidth:1, borderColor:alpha(t.success,.3), marginBottom:10 }}>
            <Text style={{ fontSize:14, fontWeight:'700', color:t.success, marginBottom:8 }}>✅ Added {result.kit.length} kit items</Text>
            {result.kit.map((k,i) => <Text key={i} style={{ fontSize:13, color:t.text, marginBottom:3 }}>• {k}</Text>)}
          </View>
          <View style={{ backgroundColor:alpha(t.accent,.1), borderRadius:10, padding:14, borderWidth:1, borderColor:alpha(t.accent,.3) }}>
            <Text style={{ fontSize:14, fontWeight:'700', color:t.accent, marginBottom:8 }}>✅ Added {result.tasks.length} tasks</Text>
            {result.tasks.map((t2,i) => <Text key={i} style={{ fontSize:13, color:t.text, marginBottom:3 }}>• {t2}</Text>)}
          </View>
        </View>
      )}

      {/* Info box */}
      {!result && (
        <View style={{ backgroundColor:t.bg2, borderRadius:10, padding:14, borderWidth:1, borderColor:t.border }}>
          <Text style={{ fontSize:13, fontWeight:'600', color:t.text, marginBottom:6 }}>How it works:</Text>
          <Text style={{ fontSize:12, color:t.text2, lineHeight:20 }}>1. Enter your Gemini API key (free at aistudio.google.com){'\n'}2. Type your region or city{'\n'}3. Tap Scan — Gemini returns hazards for your area{'\n'}4. Kit items and tasks are automatically added to your app</Text>
        </View>
      )}
    </ScrollView>
  );
}

// ── THREAT LABELS ────────────────────────────────────────────────
const THREAT_LABELS = {
  FIST_FACE:'Fist → Face', FIST_BODY:'Fist → Body',
  FIST_FIST:'Fist Collision', GUN_POSE:'Gun Pose Detected',
  ARM_SWING:'Aggressive Arm Swing', THREAT_STANCE:'Threatening Stance',
  PUNCH:'Punch Motion', PERSON_COLLISION:'Persons Too Close',
  INTRUDER:'⚠ Intruder Detected', MOTION:'⚠ Motion Detected',
  LOITER:'⚠ Person Loitering', ZONE_BREACH:'⚠ Zone Breached',
};

// ── LIVE FEED (MJPEG via rapid Image refresh) ─────────────────────
function LiveFeed({ url, t }) {
  const [ts,  setTs]  = useState(Date.now());
  const [err, setErr] = useState(false);
  useEffect(() => {
    setErr(false);
    const iv = setInterval(() => setTs(Date.now()), 150);
    return () => clearInterval(iv);
  }, [url]);
  if (err) return (
    <View style={{ flex:1, alignItems:'center', justifyContent:'center', padding:20 }}>
      <Text style={{ fontSize:30, marginBottom:8 }}>📷</Text>
      <Text style={{ color:'#fff', fontSize:13, textAlign:'center', opacity:.7 }}>
        Feed unavailable{'\n'}Check server is running
      </Text>
    </View>
  );
  return (
    <Image
      source={{ uri:`${url}?t=${ts}`, headers:{ 'Cache-Control':'no-cache' } }}
      style={{ width:'100%', height:'100%' }}
      resizeMode="contain"
      onError={() => setErr(true)}
      onLoad={() => setErr(false)}
    />
  );
}

// ── CAMERA / THREAT DETECTOR SCREEN ──────────────────────────────
function CameraScreen({ t, data, setData }) {
  const [serverIP,   setServerIP]   = useState('localhost');
  const [connected,  setConnected]  = useState(false);
  const [status,     setStatus]     = useState(null);
  const [awayMode,   setAwayMode]   = useState(false);
  const [snapshots,  setSnapshots]  = useState([]);
  const [activeTab,  setActiveTab]  = useState('live');
  const prevSosRef  = React.useRef(0);
  const pollRef     = React.useRef(null);
  const snapPollRef = React.useRef(null);

  // Accept: "192.168.1.5", "localhost", "http://192.168.1.5:5050", etc.
  function buildBase(input) {
    const s = (input || '').trim();
    if (s.startsWith('http://') || s.startsWith('https://')) {
      // Strip trailing slash and any path
      return s.replace(/\/+$/, '').split('/').slice(0,3).join('/');
    }
    // bare IP or hostname — add port 5050
    const host = s.replace(/:.*/, ''); // strip any port user typed
    return `http://${host}:5050`;
  }

  const base      = buildBase(serverIP);
  const videoURL  = `${base}/video`;
  const statusURL = `${base}/api/status`;   // /api/* has guaranteed CORS headers
  const awayURL   = `${base}/api/away`;
  const snapsURL  = `${base}/api/snapshots`;

  function startPolling() {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const ctrl = new AbortController();
        const tid = setTimeout(() => ctrl.abort(), 2500);
        const r = await fetch(statusURL, { signal: ctrl.signal, mode:'cors' });
        clearTimeout(tid);
        const s = await r.json();
        setStatus(s);
        setConnected(true);
        setAwayMode(!!s.away_mode);
        // Auto-add task if new SOS fired
        if ((s.sos_count || 0) > prevSosRef.current) {
          prevSosRef.current = s.sos_count;
          setData(d => ({...d,
            tasks:[...d.tasks, {id:Date.now()+'', text:`🚨 ${s.sos_reason}`, done:false}]
          }));
        }
      } catch {
        setConnected(false);
        setStatus(null);
      }
    }, 1000);

    // Snapshot polling
    if (snapPollRef.current) clearInterval(snapPollRef.current);
    snapPollRef.current = setInterval(async () => {
      try {
        const ctrl2 = new AbortController();
        const tid2 = setTimeout(() => ctrl2.abort(), 2000);
        const r = await fetch(snapsURL, { signal: ctrl2.signal, mode:'cors' });
        clearTimeout(tid2);
        const d = await r.json();
        setSnapshots((d.snapshots || []).reverse().slice(0, 8));
      } catch {}
    }, 3000);
  }

  function stopPolling() {
    if (pollRef.current)     { clearInterval(pollRef.current);     pollRef.current=null; }
    if (snapPollRef.current) { clearInterval(snapPollRef.current); snapPollRef.current=null; }
    setConnected(false); setStatus(null);
  }

  React.useEffect(() => () => stopPolling(), []);

  async function toggleAway() {
    const next = !awayMode;
    try {
      await fetch(awayURL, {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ active: next }),
        mode:'cors',
      });
      setAwayMode(next);
    } catch { Alert.alert('Error', 'Cannot reach server'); }
  }

  const hasThreats  = status?.confirmed?.length > 0;
  const awayAlert   = status?.away_alert;
  const peopleCount = status?.people_count || 0;
  const motionPct   = Math.min(100, ((status?.motion_level || 0) / 15000) * 100);

  // ── Sub-tab buttons ─────────────────────────────────────────────
  function TabBtn({ id, label }) {
    const active = activeTab === id;
    return (
      <TouchableOpacity onPress={() => setActiveTab(id)} style={{ flex:1, paddingVertical:8,
        alignItems:'center', backgroundColor: active ? t.accent : t.bg2,
        borderRadius:8, marginHorizontal:2 }}>
        <Text style={{ fontSize:12, fontWeight:'700', color: active ? '#fff' : t.text2 }}>{label}</Text>
      </TouchableOpacity>
    );
  }

  return (
    <ScrollView style={{ flex:1, backgroundColor:t.bg }}
      contentContainerStyle={{ padding:14, paddingBottom:30 }}
      showsVerticalScrollIndicator={false}>

      {/* Title */}
      <Text style={{ fontSize:18, fontWeight:'700', color:t.text, marginBottom:4 }}>Threat Detector</Text>
      <Text style={{ fontSize:12, color:t.text2, marginBottom:14 }}>
        Connects to threat_server.py on your PC via WiFi
      </Text>

      {/* Quick fill buttons */}
      <View style={{ flexDirection:'row', gap:8, marginBottom:8 }}>
        <Text style={{ fontSize:12, color:t.text2, alignSelf:'center' }}>Quick:</Text>
        {['localhost','192.168.1.1'].map(ip => (
          <TouchableOpacity key={ip} onPress={() => setServerIP(ip)}
            style={{ backgroundColor:t.bg2, borderRadius:6, paddingHorizontal:10, paddingVertical:5,
              borderWidth:1, borderColor:serverIP===ip?t.accent:t.border }}>
            <Text style={{ fontSize:12, color:serverIP===ip?t.accent:t.text2 }}>{ip}</Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* IP + Connect */}
      <View style={{ flexDirection:'row', gap:8, marginBottom:12 }}>
        <TextInput value={serverIP} onChangeText={setServerIP}
          placeholder="localhost  or  192.168.1.5"
          placeholderTextColor={t.text2}
          autoCapitalize="none" autoCorrect={false}
          style={{ flex:1, borderWidth:1.5, borderColor:connected?t.success:t.border,
            borderRadius:10, padding:11, fontSize:13, color:t.text, backgroundColor:t.bg2 }} />
        <TouchableOpacity onPress={connected ? stopPolling : startPolling}
          style={{ backgroundColor: connected ? t.danger : t.accent,
            borderRadius:10, paddingHorizontal:16, justifyContent:'center' }}>
          <Text style={{ color:'#fff', fontWeight:'700', fontSize:14 }}>
            {connected ? 'Stop' : 'Connect'}
          </Text>
        </TouchableOpacity>
      </View>
      <Text style={{ fontSize:11, color:t.text2, marginBottom:8, marginTop:-6 }}>
        Connecting to: <Text style={{ color:t.accent }}>{base}</Text>
        {'  '}
        <Text style={{ color:t.text2 }}>
          (use localhost if server is on this same PC)
        </Text>
      </Text>

      {/* Status row */}
      <View style={{ flexDirection:'row', alignItems:'center', gap:8, marginBottom:12,
        backgroundColor:t.bg2, borderRadius:10, padding:11,
        borderWidth:1, borderColor: connected ? t.success : t.border }}>
        <View style={{ width:9, height:9, borderRadius:5,
          backgroundColor: connected ? t.success : t.danger }} />
        <Text style={{ fontSize:13, color:t.text, fontWeight:'500', flex:1 }}>
          {connected
            ? `Connected · ${status?.fps||0} FPS · ${peopleCount} person${peopleCount!==1?'s':''}`
            : 'Not connected — enter PC IP and tap Connect'}
        </Text>
        {connected && <Text style={{ fontSize:12, color:t.text2 }}>SOS: {status?.sos_count||0}</Text>}
      </View>

      {/* Threat / away alert banner */}
      {connected && (hasThreats || awayAlert) && (
        <View style={{ backgroundColor:alpha(t.danger,.12), borderRadius:12, padding:14,
          borderWidth:2, borderColor:t.danger, marginBottom:12 }}>
          <Text style={{ fontSize:16, fontWeight:'800', color:t.danger, marginBottom:6 }}>
            🚨  {awayAlert ? 'INTRUDER ALERT' : 'THREAT DETECTED'}
          </Text>
          {(status?.confirmed||[]).map((k,i) => (
            <Text key={i} style={{ fontSize:13, color:t.danger, marginTop:2 }}>
              • {THREAT_LABELS[k]||k}
            </Text>
          ))}
        </View>
      )}

      {connected && !hasThreats && !awayAlert && (
        <View style={{ backgroundColor:alpha(t.success,.1), borderRadius:10, padding:11,
          borderWidth:1, borderColor:t.success, marginBottom:12,
          flexDirection:'row', alignItems:'center', gap:8 }}>
          <Text style={{ fontSize:14, fontWeight:'700', color:t.success }}>
            ✓  {awayMode ? 'Away Mode Armed — Watching' : 'All Clear — Monitoring'}
          </Text>
        </View>
      )}

      {/* Sub tabs */}
      {connected && (
        <View style={{ flexDirection:'row', marginBottom:12 }}>
          <TabBtn id="live"  label="📹 Live Feed" />
          <TabBtn id="away"  label="🏠 Away Mode" />
          <TabBtn id="log"   label="📋 Log" />
          <TabBtn id="snaps" label="📸 Snaps" />
        </View>
      )}

      {/* ── LIVE TAB ── */}
      {connected && activeTab==='live' && (
        <View>
          <View style={{ borderRadius:12, overflow:'hidden', borderWidth:1, borderColor:t.border,
            backgroundColor:'#000', aspectRatio:16/9 }}>
            <LiveFeed url={videoURL} t={t} />
          </View>
          <Text style={{ fontSize:11, color:t.text2, marginTop:6, textAlign:'center' }}>
            Tip: if feed is black, open{' '}
            <Text style={{ color:t.accent }}>{videoURL}</Text>
            {' '}directly in your browser to test
          </Text>
        </View>
      )}

      {/* ── AWAY MODE TAB ── */}
      {connected && activeTab==='away' && (
        <View>
          {/* Arm/Disarm button */}
          <TouchableOpacity onPress={toggleAway} style={{
            backgroundColor: awayMode ? alpha(t.danger,.15) : t.accent,
            borderRadius:12, padding:18, alignItems:'center', marginBottom:12,
            borderWidth:2, borderColor: awayMode ? t.danger : t.accent }}>
            <Text style={{ fontSize:22, marginBottom:4 }}>{awayMode ? '🔴' : '🏠'}</Text>
            <Text style={{ fontSize:16, fontWeight:'800',
              color: awayMode ? t.danger : '#fff' }}>
              {awayMode ? 'DISARM Away Mode' : 'ARM Away Mode'}
            </Text>
            <Text style={{ fontSize:12, color: awayMode ? t.danger : 'rgba(255,255,255,.7)',
              marginTop:4 }}>
              {awayMode ? 'Tap to disarm — you are back home' : 'Tap to arm — alerts if anyone enters'}
            </Text>
          </TouchableOpacity>

          {/* Motion level */}
          <View style={{ backgroundColor:t.bg2, borderRadius:12, padding:14,
            borderWidth:1, borderColor:t.border, marginBottom:10 }}>
            <Text style={{ fontSize:12, fontWeight:'600', color:t.text2,
              textTransform:'uppercase', letterSpacing:.5, marginBottom:10 }}>Motion Level</Text>
            <View style={{ backgroundColor:t.border, borderRadius:4, height:10, overflow:'hidden' }}>
              <View style={{ height:'100%', width:`${motionPct}%`, borderRadius:4,
                backgroundColor: motionPct>60?t.danger:motionPct>30?t.warning:t.accent }} />
            </View>
            <Text style={{ fontSize:11, color:t.text2, marginTop:5 }}>
              {status?.motion_level||0} px detected
            </Text>
          </View>

          {/* People count */}
          <View style={{ backgroundColor:t.bg2, borderRadius:12, padding:14,
            borderWidth:1, borderColor: awayMode&&peopleCount>0?t.danger:t.border,
            flexDirection:'row', alignItems:'center', gap:12 }}>
            <Text style={{ fontSize:36, fontWeight:'800',
              color: awayMode&&peopleCount>0?t.danger:t.text }}>
              {peopleCount}
            </Text>
            <View>
              <Text style={{ fontSize:14, fontWeight:'600', color:t.text }}>
                {peopleCount===0 ? 'No one detected' :
                 peopleCount===1 ? 'Person detected' : `${peopleCount} people detected`}
              </Text>
              <Text style={{ fontSize:12, color: awayMode&&peopleCount>0?t.danger:t.text2, marginTop:2 }}>
                {awayMode&&peopleCount>0 ? '⚠ Intruder alert!' : awayMode ? 'Area clear' : 'Away mode disarmed'}
              </Text>
            </View>
          </View>

          {/* Away mode info */}
          <View style={{ backgroundColor:alpha(t.accent,.07), borderRadius:10, padding:12,
            borderWidth:1, borderColor:alpha(t.accent,.2), marginTop:10 }}>
            <Text style={{ fontSize:13, fontWeight:'600', color:t.accent, marginBottom:6 }}>
              Away Mode detects:
            </Text>
            {['Any motion in frame','Any person appearing (intruder)','Person staying 8+ seconds (loiter)','Gun pose or aggressive movement'].map((s,i) => (
              <Text key={i} style={{ fontSize:12, color:t.text2, marginTop:3 }}>• {s}</Text>
            ))}
          </View>
        </View>
      )}

      {/* ── LOG TAB ── */}
      {connected && activeTab==='log' && (
        <View style={{ backgroundColor:t.bg2, borderRadius:12, padding:14,
          borderWidth:1, borderColor:t.border }}>
          <Text style={{ fontSize:14, fontWeight:'700', color:t.text, marginBottom:12 }}>
            SOS Event Log ({status?.sos_count||0} total)
          </Text>
          {(status?.sos_log||[]).length===0
            ? <Text style={{ fontSize:13, color:t.text2, textAlign:'center', paddingVertical:20 }}>
                No events yet
              </Text>
            : [...(status?.sos_log||[])].reverse().map((e,i,arr) => (
              <View key={i} style={{ flexDirection:'row', gap:10, paddingVertical:8,
                borderBottomWidth:i<arr.length-1?1:0, borderColor:t.border }}>
                <View style={{ width:8, height:8, borderRadius:4,
                  backgroundColor:t.danger, marginTop:4, flexShrink:0 }} />
                <View style={{ flex:1 }}>
                  <Text style={{ fontSize:11, color:t.accent, fontWeight:'600' }}>{e.time}</Text>
                  <Text style={{ fontSize:13, color:t.text, marginTop:2 }}>{e.reason}</Text>
                </View>
              </View>
            ))
          }
        </View>
      )}

      {/* ── SNAPSHOTS TAB ── */}
      {connected && activeTab==='snaps' && (
        <View>
          <Text style={{ fontSize:14, fontWeight:'700', color:t.text, marginBottom:12 }}>
            Saved Snapshots
          </Text>
          {snapshots.length === 0
            ? <View style={{ alignItems:'center', padding:30 }}>
                <Text style={{ fontSize:30, marginBottom:8 }}>📸</Text>
                <Text style={{ fontSize:13, color:t.text2 }}>No snapshots yet</Text>
                <Text style={{ fontSize:12, color:t.text2, marginTop:4 }}>
                  Snapshots are saved automatically when SOS fires
                </Text>
              </View>
            : snapshots.map((s,i) => (
              <View key={i} style={{ marginBottom:12, borderRadius:12, overflow:'hidden',
                borderWidth:1, borderColor:t.border }}>
                <Image
                  source={{ uri:`${base}/snapshots/${s.file}` }}
                  style={{ width:'100%', aspectRatio:16/9 }}
                  resizeMode="cover"
                />
                <View style={{ padding:10, backgroundColor:t.bg2 }}>
                  <Text style={{ fontSize:11, color:t.accent, fontWeight:'600' }}>{s.time}</Text>
                  <Text style={{ fontSize:12, color:t.text, marginTop:2 }}>{s.reason}</Text>
                </View>
              </View>
            ))
          }
        </View>
      )}

      {/* Setup instructions (when not connected) */}
      {!connected && (
        <View style={{ backgroundColor:alpha(t.accent,.07), borderRadius:12, padding:14,
          borderWidth:1, borderColor:alpha(t.accent,.2) }}>
          <Text style={{ fontSize:14, fontWeight:'700', color:t.accent, marginBottom:10 }}>
            How to start the server on your PC:
          </Text>
          {[
            'pip install opencv-python mediapipe flask flask-cors',
            'python threat_server.py',
            '# Auto-opens browser at http://localhost:5050',
            '# Find your PC IP:  run  ipconfig  in cmd',
            '# Enter that IP above and tap Connect',
          ].map((line,i) => (
            <View key={i} style={{ backgroundColor:t.bg, borderRadius:6, padding:8, marginBottom:6 }}>
              <Text style={{ fontSize:11,
                color: line.startsWith('#') ? t.text2 : t.text,
                fontFamily:'monospace' }}>{line}</Text>
            </View>
          ))}
        </View>
      )}

    </ScrollView>
  );
}

// ══════════════════════════════════════════════════════════════════
//  NAV BAR
// ══════════════════════════════════════════════════════════════════
const TABS = [
  { key:'home',     label:'Home',     icon:'🏠' },
  { key:'kit',      label:'Kit',      icon:'📦' },
  { key:'sos',      label:'SOS',      icon:'🚨' },
  { key:'ai',       label:'AI Scout', icon:'🤖' },
  { key:'camera',   label:'Camera',   icon:'📷' },
  { key:'settings', label:'Settings', icon:'⚙️' },
];

function NavBar({ active, onPress, t }) {
  return (
    <View style={{ flexDirection:'row', borderTopWidth:1, borderColor:t.border, backgroundColor:t.bg }}>
      {TABS.map(tab => {
        const isSOS    = tab.key==='sos';
        const isActive = tab.key===active;
        const color    = isSOS ? t.danger : isActive ? t.accent : t.text2;
        return (
          <TouchableOpacity key={tab.key} onPress={()=>onPress(tab.key)}
            style={{ flex:1, paddingVertical:8, alignItems:'center', gap:3 }}>
            <Text style={{ fontSize:isSOS?22:20 }}>{tab.icon}</Text>
            <Text style={{ fontSize:10, fontWeight:'600', color }}>{tab.label}</Text>
          </TouchableOpacity>
        );
      })}
    </View>
  );
}

// ══════════════════════════════════════════════════════════════════
//  APP
// ══════════════════════════════════════════════════════════════════
export default function App() {
  const [data, setDataRaw]    = useState(DEFAULT);
  const [tab,  setTab]        = useState('home');
  const [themeName, setThemeNameRaw] = useState('modern');
  const t = THEMES[themeName] || THEMES.modern;

  // Auto-save
  function setData(updater) {
    setDataRaw(prev => {
      const next = typeof updater==='function' ? updater(prev) : updater;
      AsyncStorage.setItem(SAVE_KEY, JSON.stringify({...next, theme:themeName})).catch(()=>{});
      return next;
    });
  }

  function setThemeName(name) {
    setThemeNameRaw(name);
    AsyncStorage.setItem(SAVE_KEY, JSON.stringify({...data, theme:name})).catch(()=>{});
  }

  useEffect(() => {
    AsyncStorage.getItem(SAVE_KEY).then(s => {
      if (s) {
        const d = JSON.parse(s);
        if (d.theme) setThemeNameRaw(d.theme);
        setDataRaw({...DEFAULT, ...d});
      }
    }).catch(()=>{});
  }, []);

  const screenProps = { data, setData, t };

  return (
    <SafeAreaView style={{ flex:1, backgroundColor:t.primary }}>
      <StatusBar barStyle="light-content" backgroundColor={t.primary} />

      {/* Header */}
      <View style={{ backgroundColor:t.primary, paddingHorizontal:16, paddingVertical:12, flexDirection:'row', alignItems:'center', justifyContent:'space-between' }}>
        <View>
          <Text style={{ fontSize:20, fontWeight:'700', color:'#fff' }}>StepPrep</Text>
          <Text style={{ fontSize:11, color:'rgba(255,255,255,.7)', marginTop:1 }}>Emergency Preparedness</Text>
        </View>
        <Text style={{ fontSize:11, color:'rgba(255,255,255,.6)' }}>Theme in Settings ›</Text>
      </View>

      {/* Screen */}
      <View style={{ flex:1, position:'relative' }}>
        {tab==='home'     && <HomeScreen     {...screenProps} />}
        {tab==='kit'      && <KitScreen      {...screenProps} />}
        {tab==='sos'      && <SOSScreen      {...screenProps} />}
        {tab==='plan'     && <PlanScreen     {...screenProps} />}
        {tab==='ai'       && <AIScreen       {...screenProps} />}
        {tab==='camera'   && <CameraScreen   {...screenProps} />}
        {tab==='settings' && <SettingsScreen {...screenProps} themeName={themeName} setThemeName={setThemeName} t={t} />}
      </View>

      {/* Nav */}
      <NavBar active={tab} onPress={setTab} t={t} />
    </SafeAreaView>
  );
}
