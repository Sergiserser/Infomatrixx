import React, { useState, useEffect, useRef } from 'react';
import {
  View, Text, ScrollView, TouchableOpacity, TextInput,
  StyleSheet, SafeAreaView, StatusBar, Alert, Animated,
  Modal, KeyboardAvoidingView, Platform, Dimensions,
  FlatList, Pressable,
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

// ── Input Modal ───────────────────────────────────────────────────
function InputModal({ visible, title, fields, onSubmit, onCancel, t }) {
  const [vals, setVals] = useState({});
  useEffect(() => { if (visible) setVals({}) }, [visible]);
  return (
    <Modal visible={visible} transparent animationType="slide">
      <KeyboardAvoidingView behavior={Platform.OS==='ios'?'padding':'height'} style={{ flex:1, justifyContent:'flex-end' }}>
        <Pressable style={{ flex:1 }} onPress={onCancel} />
        <View style={{ backgroundColor:t.bg, borderTopLeftRadius:20, borderTopRightRadius:20, padding:20, borderTopWidth:1, borderColor:t.border }}>
          <View style={{ width:36, height:4, backgroundColor:t.border, borderRadius:2, alignSelf:'center', marginBottom:16 }} />
          <Text style={{ fontSize:18, fontWeight:'700', color:t.text, textAlign:'center', marginBottom:18 }}>{title}</Text>
          {fields.map(f => (
            <View key={f.id} style={{ marginBottom:12 }}>
              <Text style={{ fontSize:12, color:t.text2, fontWeight:'500', marginBottom:5 }}>{f.label}</Text>
              <TextInput
                placeholder={f.placeholder}
                placeholderTextColor={t.text2}
                value={vals[f.id]||''}
                onChangeText={v => setVals(prev => ({...prev, [f.id]:v}))}
                secureTextEntry={f.secure||false}
                style={{ borderWidth:1.5, borderColor:t.border, borderRadius:8, padding:11, fontSize:14, color:t.text, backgroundColor:t.bg2 }}
              />
            </View>
          ))}
          <View style={{ flexDirection:'row', gap:10, marginTop:8 }}>
            <GhostButton label="Cancel" onPress={onCancel} t={t} style={{ flex:1 }} />
            <PrimaryButton label="Save" onPress={() => onSubmit(vals)} t={t} style={{ flex:1 }} />
          </View>
        </View>
      </KeyboardAvoidingView>
    </Modal>
  );
}

// ── Confirm Modal ─────────────────────────────────────────────────
function ConfirmModal({ visible, message, onConfirm, onCancel, t }) {
  return (
    <Modal visible={visible} transparent animationType="fade">
      <View style={{ flex:1, backgroundColor:'rgba(0,0,0,.5)', justifyContent:'center', alignItems:'center', padding:24 }}>
        <View style={{ backgroundColor:t.bg, borderRadius:16, padding:24, width:'100%', maxWidth:300, borderWidth:1, borderColor:t.border }}>
          <Text style={{ fontSize:16, fontWeight:'700', color:t.text, textAlign:'center', marginBottom:6 }}>{message}</Text>
          <Text style={{ fontSize:13, color:t.text2, textAlign:'center', marginBottom:20 }}>This cannot be undone.</Text>
          <View style={{ flexDirection:'row', gap:10 }}>
            <GhostButton label="Cancel" onPress={onCancel} t={t} style={{ flex:1 }} />
            <TouchableOpacity onPress={onConfirm} style={{ flex:1, backgroundColor:t.danger, borderRadius:10, paddingVertical:13, alignItems:'center' }}>
              <Text style={{ color:'#fff', fontWeight:'700', fontSize:15 }}>Delete</Text>
            </TouchableOpacity>
          </View>
        </View>
      </View>
    </Modal>
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
    if (!vals.f0) return;
    setData(d => ({...d, tasks:[...d.tasks,{id:Date.now()+'',text:vals.f0,done:false}]}));
    setModal(false);
  }

  function delTask(id) {
    setData(d => ({...d, tasks:d.tasks.filter(t=>t.id!==id)}));
    setConfirm(null);
  }

  return (
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

      <InputModal visible={modal} title="New Task" fields={[{id:'f0',label:'Description',placeholder:'e.g. Check water supply'}]} onSubmit={addTask} onCancel={()=>setModal(false)} t={t} />
      {confirm && <ConfirmModal visible message={confirm.msg} onConfirm={confirm.cb} onCancel={()=>setConfirm(null)} t={t} />}
    </ScrollView>
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
    if (!vals.f0) return;
    setData(d => ({...d, supplies:[...d.supplies,{id:Date.now()+'',name:vals.f0,qty:vals.f1||'',status:'ok',cat:vals.f2||'tools'}]}));
    setModal(false);
  }

  function delSupply(id) {
    setData(d => ({...d, supplies:d.supplies.filter(s=>s.id!==id)}));
    setConfirm(null);
  }

  const ok  = data.supplies.filter(s=>s.status==='ok').length;
  const pct = data.supplies.length ? Math.round(ok/data.supplies.length*100) : 0;

  return (
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

      <InputModal visible={modal} title="Add Supply" fields={[
        {id:'f0',label:'Item name',placeholder:'e.g. Bottled water'},
        {id:'f1',label:'Quantity',placeholder:'e.g. 12 L'},
        {id:'f2',label:'Category',placeholder:'water-food / medical / tools'},
      ]} onSubmit={addSupply} onCancel={()=>setModal(false)} t={t} />
      {confirm && <ConfirmModal visible message={confirm.msg} onConfirm={confirm.cb} onCancel={()=>setConfirm(null)} t={t} />}
    </ScrollView>
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
    if (!vals.f0) return;
    setData(d => ({...d, contacts:[...d.contacts,{id:Date.now()+'',name:vals.f0,phone:vals.f1||'',role:vals.f2||'',initials:vals.f0.split(' ').map(x=>x[0]).join('').toUpperCase().slice(0,2),primary:false}]}));
    setModal(false);
  }

  function delContact(id) {
    setData(d => ({...d, contacts:d.contacts.filter(c=>c.id!==id)}));
    setConfirm(null);
  }

  return (
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

      <InputModal visible={modal} title="New Contact" fields={[
        {id:'f0',label:'Name',placeholder:'Full name'},
        {id:'f1',label:'Phone',placeholder:'+1 555 000 0000'},
        {id:'f2',label:'Role',placeholder:'e.g. Family, Neighbour'},
      ]} onSubmit={addContact} onCancel={()=>setModal(false)} t={t} />
      {confirm && <ConfirmModal visible message={confirm.msg} onConfirm={confirm.cb} onCancel={()=>setConfirm(null)} t={t} />}
    </ScrollView>
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

// ══════════════════════════════════════════════════════════════════
//  NAV BAR
// ══════════════════════════════════════════════════════════════════
const TABS = [
  { key:'home',     label:'Home',     icon:'🏠' },
  { key:'kit',      label:'Kit',      icon:'📦' },
  { key:'sos',      label:'SOS',      icon:'🚨' },
  { key:'plan',     label:'Plan',     icon:'🗺️' },
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
        <View style={{ flexDirection:'row', gap:6 }}>
          {Object.entries(THEMES).map(([key,th]) => (
            <TouchableOpacity key={key} onPress={()=>setThemeName(key)}
              style={{ width:16, height:16, borderRadius:8, backgroundColor:th.primary,
                borderWidth:2, borderColor:themeName===key?'#fff':'transparent' }} />
          ))}
        </View>
      </View>

      {/* Screen */}
      <View style={{ flex:1 }}>
        {tab==='home'     && <HomeScreen     {...screenProps} />}
        {tab==='kit'      && <KitScreen      {...screenProps} />}
        {tab==='sos'      && <SOSScreen      {...screenProps} />}
        {tab==='plan'     && <PlanScreen     {...screenProps} />}
        {tab==='settings' && <SettingsScreen {...screenProps} themeName={themeName} setThemeName={setThemeName} t={t} />}
      </View>

      {/* Nav */}
      <NavBar active={tab} onPress={setTab} t={t} />
    </SafeAreaView>
  );
}
