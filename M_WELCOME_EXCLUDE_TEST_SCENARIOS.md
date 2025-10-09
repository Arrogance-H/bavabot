# M欢迎排除列表测试场景 / M Welcome Exclusion List Test Scenarios

## 测试场景 / Test Scenarios

### 场景1: 正常M用户（未被排除）
**Setup:**
- User ID: 123456789
- In `m_users`: ✅ Yes
- In `m_welcome_exclude`: ❌ No
- In database: ✅ Yes
- Today's welcome sent: ❌ No

**Expected Result:** 
✅ User receives welcome message

**Log Output:**
```
【M尊享欢迎】- 欢迎M尊享用户 张三 (ID: 123456789)
```

---

### 场景2: M用户在排除列表中
**Setup:**
- User ID: 123456789
- In `m_users`: ✅ Yes
- In `m_welcome_exclude`: ✅ Yes
- In database: ✅ Yes

**Expected Result:** 
🚫 User does NOT receive welcome message (early return before DB query)

**Log Output:**
```
【M尊享欢迎】- 用户 张三 (ID: 123456789) 在排除列表中，跳过欢迎
```

---

### 场景3: 非M用户（不在m_users）
**Setup:**
- User ID: 999888777
- In `m_users`: ❌ No
- In `m_welcome_exclude`: ❌ No

**Expected Result:** 
🚫 User does NOT receive welcome message (not an M user)

**Log Output:**
None (early return, no log)

---

### 场景4: M用户在排除列表，但不在数据库
**Setup:**
- User ID: 123456789
- In `m_users`: ✅ Yes
- In `m_welcome_exclude`: ✅ Yes
- In database: ❌ No

**Expected Result:** 
🚫 User does NOT receive welcome message (excluded before DB check)

**Log Output:**
```
【M尊享欢迎】- 用户 张三 (ID: 123456789) 在排除列表中，跳过欢迎
```

---

### 场景5: 添加用户到排除列表
**Steps:**
1. Admin sends `/config`
2. Click "🚫 M欢迎排除列表"
3. Send `add 123456789`

**Expected Result:**
✅ User 123456789 added to exclusion list
✅ Config file updated
✅ Global variable updated

**Response:**
```
✅ 已添加用户 123456789 到M欢迎排除列表

当前列表：
123456789

操作完成！
```

---

### 场景6: 从排除列表移除用户
**Steps:**
1. Admin sends `/config`
2. Click "🚫 M欢迎排除列表"
3. Send `del 123456789`

**Expected Result:**
✅ User 123456789 removed from exclusion list
✅ Config file updated
✅ Global variable updated

**Response:**
```
✅ 已从M欢迎排除列表移除用户 123456789

当前列表：
无

操作完成！
```

---

### 场景7: 查看排除列表
**Steps:**
1. Admin sends `/config`
2. Click "🚫 M欢迎排除列表"
3. Send `list`

**Expected Result:**
✅ Shows all excluded user IDs

**Response:**
```
🚫【M尊享欢迎排除列表】

123456789, 987654321

操作完成！
```

---

## 性能验证 / Performance Verification

### 优化前后对比 / Before and After Comparison

**场景：M用户在排除列表中发送消息**

#### 优化前 (如果没有排除列表)
1. 检查用户是否在m_users ✓
2. 查询数据库获取用户信息 (耗时)
3. 检查今天是否已欢迎
4. 发送欢迎消息

**总耗时**: ~100-200ms (包括DB查询)

#### 优化后 (有排除列表)
1. 检查用户是否在m_users ✓
2. **检查用户是否在排除列表 ✓ (新增，O(1))**
3. 早期返回，跳过所有后续操作

**总耗时**: ~1-5ms (只是列表查找)

**性能提升**: 20-200倍 (对于被排除的用户)

---

## 手动测试步骤 / Manual Test Steps

### 准备工作 / Preparation

1. 确保bot已启动并连接到测试群组
2. 准备两个测试M用户账号
3. 确保两个用户都在`m_users`列表中

### 测试步骤 / Test Steps

#### Test 1: 添加到排除列表
1. 用户A在群组发送消息 → 应收到欢迎消息 ✓
2. Admin使用`/config` → "🚫 M欢迎排除列表" → `add [用户A的ID]`
3. 等待24小时或清空数据库中的m_welcome_date
4. 用户A再次发送消息 → **不应**收到欢迎消息 ✗
5. 查看日志确认有"在排除列表中，跳过欢迎"的消息

#### Test 2: 从排除列表移除
1. 用户A在排除列表中
2. Admin使用`/config` → "🚫 M欢迎排除列表" → `del [用户A的ID]`
3. 等待24小时或清空数据库中的m_welcome_date
4. 用户A发送消息 → 应收到欢迎消息 ✓

#### Test 3: 查看列表
1. Admin使用`/config` → "🚫 M欢迎排除列表" → `list`
2. 验证显示的用户ID是否正确

#### Test 4: 多用户场景
1. 添加用户A和用户B到排除列表
2. 用户A发送消息 → 不应收到欢迎 ✗
3. 用户B发送消息 → 不应收到欢迎 ✗
4. 用户C (不在排除列表) 发送消息 → 应收到欢迎 ✓

---

## 故障排查清单 / Troubleshooting Checklist

如果功能不工作，检查以下项目：

- [ ] Bot是否正确启动？
- [ ] 配置文件中是否有`m_welcome_exclude`字段？
- [ ] 用户ID是否正确（数字类型，不是字符串）？
- [ ] 是否在添加/删除后重启了bot（如果手动编辑配置文件）？
- [ ] 是否检查了日志输出？
- [ ] m_users列表中是否包含该用户？
- [ ] 数据库连接是否正常？

---

## 性能监控 / Performance Monitoring

建议监控以下指标：

1. **欢迎消息发送次数** - 应减少（对于被排除的用户）
2. **数据库查询次数** - 应减少（被排除的用户不查询）
3. **handler执行时间** - 应减少（早期返回）
4. **日志中的"跳过欢迎"消息数量** - 验证排除功能是否生效

---

**测试完成标准 / Test Completion Criteria:**

✅ 所有场景都按预期工作
✅ 日志输出正确
✅ 性能提升可测量
✅ 无异常或错误
