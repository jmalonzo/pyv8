#pragma once

#include <vector>

#include "Wrapper.h"
#include "Utils.h"

#include <v8-debug.h>

class CDebug
{
  bool m_enabled;

  py::object m_onDebugEvent;
  py::object m_onDebugMessage;

  v8::Persistent<v8::Context> m_debug_context, m_eval_context;

  static void OnDebugEvent(const v8::Debug::EventDetails& details);
  static void OnDebugMessage(const v8::Debug::Message& message);

  void Init(void);
public:
  CDebug() : m_enabled(false)
  {
    Init();
  }

  v8::Handle<v8::Context> DebugContext() const { return v8::Local<v8::Context>::New(v8::Isolate::GetCurrent(), m_debug_context); }
  v8::Handle<v8::Context> EvalContext() const { return v8::Local<v8::Context>::New(v8::Isolate::GetCurrent(), m_eval_context); }

  bool IsEnabled(void) { return m_enabled; }
  void SetEnable(bool enable);

  void DebugBreak(void) { v8::Debug::DebugBreak(v8::Isolate::GetCurrent()); }
  void CancelDebugBreak(void) { v8::Debug::CancelDebugBreak(v8::Isolate::GetCurrent()); }

  py::object GetDebugContext(void);
  py::object GetEvalContext(void);

  static CDebug& GetInstance(void)
  {
    static CDebug s_instance;

    return s_instance;
  }

  static void Expose(void);
};
