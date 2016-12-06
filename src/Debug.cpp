#include "Debug.h"

#include <sstream>
#include <string>

#ifdef SUPPORT_DEBUGGER
  #include "V8Internal.h"
#endif

#include "Context.h"

void CDebug::Init(void)
{
  v8::HandleScope scope(v8::Isolate::GetCurrent());

  v8::Handle<v8::ObjectTemplate> global_template = v8::ObjectTemplate::New();

  v8::Handle<v8::Context> context = v8::Context::New(v8::Isolate::GetCurrent(), NULL, global_template);

  m_debug_context.Reset(v8::Isolate::GetCurrent(), context);
  DebugContext()->SetSecurityToken(v8::Undefined(v8::Isolate::GetCurrent()));

#ifdef SUPPORT_DEBUGGER
  v8::Context::Scope context_scope(DebugContext());

  // Install the debugger object in the utility scope
  v8i::Debug *debug = v8i::Isolate::Current()->debug();

  debug->Load();

  v8i::Handle<v8i::JSObject> js_debug(debug->debug_context()->global_object());
  DebugContext()->Global()->Set(v8::String::NewFromUtf8(v8::Isolate::GetCurrent(), "$debug"), v8::Utils::ToLocal(js_debug));

  // Set the security token of the debug context to allow access.
  debug->debug_context()->set_security_token(v8i::Isolate::Current()->heap()->undefined_value());
#endif
}

void CDebug::SetEnable(bool enable)
{
  if (m_enabled == enable) return;

  m_enabled = enable;

  if (enable)
  {
    BEGIN_HANDLE_JAVASCRIPT_EXCEPTION
    {
      v8::HandleScope scope(v8::Isolate::GetCurrent());

      v8::Handle<v8::External> data = v8::External::New(v8::Isolate::GetCurrent(), this);

      v8::Debug::SetDebugEventListener(v8::Isolate::GetCurrent(), OnDebugEvent, data);
      v8::Debug::SetMessageHandler(v8::Isolate::GetCurrent(), OnDebugMessage);
    }
    END_HANDLE_JAVASCRIPT_EXCEPTION
  }
}

py::object CDebug::GetDebugContext(void)
{
  v8::HandleScope handle_scope(v8::Isolate::GetCurrent());

  return py::object(py::handle<>(boost::python::converter::shared_ptr_to_python<CContext>(
    CContextPtr(new CContext(DebugContext())))));
}

void CDebug::OnDebugEvent(const v8::Debug::EventDetails& details)
{
  v8::HandleScope scope(v8::Isolate::GetCurrent());
  CDebug *pThis;

  BEGIN_HANDLE_JAVASCRIPT_EXCEPTION
  {
    pThis = static_cast<CDebug *>(v8::Handle<v8::External>::Cast(details.GetCallbackData())->Value());
  }
  END_HANDLE_JAVASCRIPT_EXCEPTION

  if (!pThis->m_enabled) return;

  if (pThis->m_onDebugEvent.is_none()) return;

  CPythonGIL python_gil;

  BEGIN_HANDLE_PYTHON_EXCEPTION
  {
    py::call<void>(pThis->m_onDebugEvent.ptr(), details.GetEvent(),
      CJavascriptObjectPtr(new CJavascriptObject(details.GetExecutionState())),
      CJavascriptObjectPtr(new CJavascriptObject(details.GetEventData())));
  }
  END_HANDLE_PYTHON_EXCEPTION
}

class DebugClientData : public v8::Debug::ClientData
{
  py::object m_data;
public:
  DebugClientData(py::object data) : m_data(data) {}

  py::object data(void) const { return m_data; }
};

void CDebug::OnDebugMessage(const v8::Debug::Message& message)
{
  if (GetInstance().m_onDebugMessage.is_none()) return;

  v8::HandleScope scope(v8::Isolate::GetCurrent());

  v8::String::Utf8Value str(message.GetJSON());

  py::object data;

  if (message.GetClientData())
  {
    data = static_cast<DebugClientData *>(message.GetClientData())->data();
  }

  CPythonGIL python_gil;

  BEGIN_HANDLE_PYTHON_EXCEPTION
  {
    py::call<void>(GetInstance().m_onDebugMessage.ptr(), py::str(*str, str.length()), data);
  }
  END_HANDLE_PYTHON_EXCEPTION
}

void CDebug::Expose(void)
{
  py::class_<CDebug, boost::noncopyable>("JSDebug", py::no_init)
    .add_property("enabled", &CDebug::IsEnabled, &CDebug::SetEnable)
    .add_property("context", &CDebug::GetDebugContext)

    .def("debugBreak", &CDebug::DebugBreak)
    .def("cancelDebugBreak", &CDebug::CancelDebugBreak)

    .def_readwrite("onDebugEvent", &CDebug::m_onDebugEvent)
    .def_readwrite("onDebugMessage", &CDebug::m_onDebugMessage)
    ;

  py::enum_<v8::DebugEvent>("JSDebugEvent")
    .value("Break", v8::Break)
    .value("Exception", v8::Exception)
    .value("AfterCompile", v8::AfterCompile)
    .value("CompileError", v8::CompileError)
    .value("AsyncTaskEvent", v8::AsyncTaskEvent)
    ;

  def("debug", &CDebug::GetInstance,
    py::return_value_policy<py::reference_existing_object>());
}
