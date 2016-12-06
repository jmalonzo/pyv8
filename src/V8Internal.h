#pragma once

#undef COMPILER
#undef TRUE
#undef FALSE

#include "src/v8.h"

#include "src/bootstrapper.h"
#include "src/globals.h"
#include "src/api.h"
#include "src/ast/scopes.h"
#include "src/base/platform/platform.h"
#include "src/debug/debug.h"
#include "src/ic/stub-cache.h"
#include "src/heap/heap.h"

#include "src/parsing/parser.h"
#include "src/compiler.h"
#include "src/parsing/scanner.h"

#include "src/snapshot/snapshot.h"
#include "src/snapshot/startup-serializer.h"


namespace v8i = v8::internal;
