# -*- coding:utf-8 -*-
__author__ = 'zhwx'
from sqlalchemy import Column,Integer,and_
from sqlalchemy import func
from sqlalchemy.orm import load_only
import json


#节点相对位置
class TREE_NODE_POSITION(object):
    LastChild=0
    FirstChild=1
    NextSibling=2
    PreviousSibling=3

#节点关系
class TREE_NODE_RELATION(object):
    Self=0
    Parent=1
    Child=2
    Siblings=3
    Descendants=4
    Ancestors=5
    Diff_tree=6
    Same_tree=7
    Same_level=8
    Unknow=9

class TreeNodeOnlyOneRootException(Exception):
    u"""一棵树只能有一个根节点，可以通过指定不同的tree_id来创建一个新树"""
    pass

class TreeNodeNotFound(Exception):
    u"""节点不存在"""
    pass

class TreeNodeInvalidOperation(Exception):
    u""" 非法节点操作"""
    pass


class TreeManager(object):
    """
    树形模式管理器,主要提供全局管理方法
    使用方法,例：
       class FileSystem(ModelBase,TreeMixins):  一个基于TreeMixins的类，提供树形存储管理
            __tree_key__="name"
            pass

        ModelBase需要提供一个session方法，返回一个sqlalchemy session对象

        #树形管理器提供更多的功能
        tree=TreeManager(FileSystem)#提供ORM类对象
        tree.get_roots()
        tree.get_children(node,include_self=True)

        file=FileSystem(tree_manager=tree)#提供TreeManager实例时，可以为节点提供更多实例方法，如果没有提供则会自行创建一个
        #实例方法只针对当前节点
        file.is_root()#主要根节点
        file.get_parent()#取得父节点

    """


    def __init__(self,model_class=None,session=None):
        """
        :param model_class: 提供一个ORM类
        :param session: 提供数据会话对象，如果没有提供则使用户ORM的类方法session取得会话
        :return:
        """
        self.init(model_class,session)

    def init(self,model_class,session):
        self._model_class=model_class
        if session is None and hasattr(self._model_class,"session"):
            self._session=self._model_class.session
        else:
            self._session=session

    def _get_tree_sort_key(self):
        """
        取得树的排序Key，优先采用__tree_sort__定义的字段，如果没有指定，则采用__tree_key__
        """
        if hasattr(self._model_class,"__tree_sort__"):
            return self._model_class.__tree_sort__
        else:
            return self._model_class.__tree_key__

    def get_nodes(self,tree_id=None,level=0):
        """
            返回指定tree_id的树
        :param tree_id: 树id，如果没有指定tree_id，则返加所有树
        :param level:限制层次,1：只返回根节点，2：返回第二级
        :return:
        """
        session=self._session
        cls=self._model_class
        if tree_id is None:
            if level==0:
                return session.query(cls).order_by(self._get_tree_sort_key(),"tree_left").all()
            else:
                return session.query(cls).filter(cls.tree_level<=level).order_by(self._get_tree_sort_key(),"tree_left").all()
        else:
            if level==0:
                return session.query(cls).filter(cls.__dict__[cls.__tree_key__]==tree_id).order_by(self._get_tree_sort_key(),"tree_left").all()
            else:
                return session.query(cls).filter(and_(cls.__dict__[cls.__tree_key__]==tree_id,cls.tree_level<=level)).order_by(self._get_tree_sort_key(),"tree_left").all()

    def get_root_node(self,node):
        """
        取得node所在树的根节点
        :param node:
        :return:如果出错则返回None
        """
        session=self._session
        cls=self._model_class

        tree_id=self.get_node_tree_id(node)
        try:
            return session.query(cls).filter(and_(cls.__dict__[cls.__tree_key__]==tree_id,cls.tree_left==1)).one()
        except Exception,E:
            return None

    def get_tree_key_field(self):
        """取得标识树的id字段"""
        return self._model_class.__table__.columns[self._model_class.__tree_id__]

    def get_tree_key_field_name(self):
        return self._model_class.__tree_key__

    def get_primary_field(self):
        """
            取得节点主关键字字段对象
        """
        if hasattr(self._model_class,"__tree_primary_key__"):
            return self._model_class.__table__.columns[self._model_class.__tree_primary_key__]
        else:#如果没有指定__tree_node_pk__,则自动提供主关键字
            return self._model_class.__table__.primary_key.columns.values()[0]
    def get_node_primary(self,node):
        """
        取得节点的pk值
        :param node:
        :return:
        """
        return node.__dict__[self.get_primary_field().name]

    def get_node_tree_id(self,node):
        """取得节点所属的tree id 值"""
        tree_id=node.__dict__[self._model_class.__tree_key__] if hasattr(node,self._model_class.__tree_key__) else 0
        tree_id=0 if tree_id is None else tree_id
        return tree_id

    def add_node(self,nodes, ref_node=None, pos=TREE_NODE_POSITION.LastChild,tree_id=None):
        """
            增加一个或多个节点
            nodes:可以是一个TreeMixin实例，也可以是一个[]，如[Node1,Node2,{"name":"xxX"}]，不支持树形结构
            refnode:相对节点,如果=None则说明增加为根节点
            pos:相对refnode的位置，默认0:最后子节点，1:第一个子节点,2:下一节点，3:上一节点
            使用方法:
                node=Node(...)
                Node.add_node(node)
            ref_node:要增加的相对节点，如果没有指定，则增加为根节点
        """
        session=self._session
        cls=self._model_class

        if isinstance(nodes,list):
            #转化里面的Dict实例，并过滤掉所有非TreeMixin实例
            nodes=[self._model_class(**child_node) if isinstance(child_node,dict) else child_node for child_node in nodes if isinstance(child_node,TreeMixin) or isinstance(child_node,dict)]
            added_node_count=len(nodes)
        elif isinstance(nodes,TreeMixin):
            nodes=[nodes]
            added_node_count=1  #要增加的节点数量

        #取得要增加的树id，要求所有节点必须是同一棵树
        tree_id=self.get_node_tree_id(nodes[0]) if tree_id is None else tree_id

        # 增加根节点,一棵树只能有一个根节点
        # 如果nodes有多个，说明要新增多个根节点，或者多棵树
        if ref_node is None:
            #判断该树是否已经存在root节点
            has_root_node=session.query(session.query(cls).filter(and_(cls.__dict__[cls.__tree_key__]==tree_id,cls.tree_left==1)).exists()).scalar()
            #根节点已经存在,触发错误
            if has_root_node:
                raise TreeNodeOnlyOneRootException
            #开始增加根节点，不同的根节点代表不同的树
            for i in range(added_node_count):
                nodes[i].__dict__.update({
                    "tree_left":1,
                    "tree_right":2,
                    "tree_level":1
                })
        else:
            #保存相对节点的基本数据
            ref_right=ref_node.tree_right;ref_left=ref_node.tree_left
            ref_level=ref_node.tree_level;ref_tree_id=self.get_node_tree_id(ref_node)

            if pos==TREE_NODE_POSITION.LastChild:#增加为最后一个子节点
                for i in range(added_node_count):
                    nodes[i].__dict__.update({
                        cls.__tree_key__:ref_tree_id,
                        "tree_left":ref_right+i*2,
                        "tree_right":ref_right+i*2+1,
                        "tree_level":ref_level+1
                    })
                self._session.query(cls)\
                    .filter(and_(cls.tree_right>=ref_right,cls.__dict__[cls.__tree_key__]==ref_tree_id))\
                    .update({cls.tree_right:cls.tree_right+added_node_count*2})
                self._session.query(cls)\
                    .filter(and_(cls.tree_left>=ref_right,cls.__dict__[cls.__tree_key__]==ref_tree_id))\
                    .update({cls.tree_left:cls.tree_left+added_node_count*2})
            elif pos==TREE_NODE_POSITION.FirstChild:#增加为第一个子节点
                for i in range(len(nodes)):
                    nodes[i].__dict__.update({
                        cls.__tree_key__:ref_tree_id,
                        "tree_left":ref_left+i*2+1,
                        "tree_right":ref_left+i*2+2,
                        "tree_level":ref_level+1
                    })
                session.query(cls)\
                    .filter(and_(cls.tree_left>ref_left,cls.__dict__[cls.__tree_key__]==ref_tree_id))\
                    .update({cls.tree_left:cls.tree_left+added_node_count*2})
                session.query(cls)\
                    .filter(and_(cls.tree_right>=ref_left+1,cls.__dict__[cls.__tree_key__]==ref_tree_id))\
                    .update({cls.tree_right:cls.tree_right+added_node_count*2})
            elif pos==TREE_NODE_POSITION.NextSibling:#增加为下一个兄弟节点
                for i in range(len(nodes)):
                    nodes[i].__dict__.update({
                        cls.__tree_key__:ref_tree_id,
                        "tree_left":ref_right+i*2+1,
                        "tree_right":ref_right+i*2+2,
                        "tree_level":ref_level
                    })
                self._session.query(cls).\
                    filter(and_(cls.tree_left>ref_right,cls.__dict__[cls.__tree_key__]==ref_tree_id))\
                    .update({cls.tree_left:cls.tree_left+added_node_count*2})
                self._session.query(cls)\
                    .filter(and_(cls.tree_right>ref_right,cls.__dict__[cls.__tree_key__]==ref_tree_id))\
                    .update({cls.tree_right:cls.tree_right+added_node_count*2})
            elif pos==TREE_NODE_POSITION.PreviousSibling:#增加为上一个兄弟节点
                for i in range(len(nodes)):
                    nodes[i].__dict__.update({
                        cls.__tree_key__:ref_tree_id,
                        "tree_left":ref_left+i*2,
                        "tree_right":ref_left+i*2+1,
                        "tree_level":ref_level
                    })
                self._session.query(cls)\
                    .filter(and_(cls.tree_left>=ref_left,cls.__dict__[cls.__tree_key__]==ref_tree_id))\
                    .update({cls.tree_left:cls.tree_left+added_node_count*2})
                self._session.query(cls)\
                    .filter(and_(cls.tree_right>=ref_left+1,cls.__dict__[cls.__tree_key__]==ref_tree_id))\
                    .update({cls.tree_right:cls.tree_right+added_node_count*2})

        #提交增加节点到会话
        if len(nodes)==1:
            session.add(nodes[0])
        else:
            session.add_all(nodes)

    def del_node(self,node):
        """ 删除指定的节点 """

        cls=self._model_class
        lft=node.tree_left
        rgt=node.tree_right
        self._session.query(cls)\
            .filter(and_(cls.tree_left>=lft,cls.tree_right<=rgt,cls.__dict__[cls.__tree_key__]==self.get_node_tree_id(node)))\
            .delete()
        self._session.query(cls)\
            .filter(and_(cls.tree_left>lft,cls.__dict__[cls.__tree_key__]==self.get_node_tree_id(node)))\
            .update({cls.tree_left:cls.tree_left-(rgt-lft+1)})
        self._session.query(cls)\
            .filter(and_(cls.tree_right>rgt,cls.__dict__[cls.__tree_key__]==self.get_node_tree_id(node)))\
            .update({cls.tree_right:cls.tree_right-(rgt-lft+1)})

    def move_node(self,node,ref_node,pos=0):
        """
            移动节点node到refnode的相对位置，连同该节点下属的所有子节点
            相对refnode的位置，0:最后子节点，1:第一个子节点,2:下一节点，3:上一节点

            注意：如果node和ref_node属于不同的树，则node将移到另一棵树中
         """

        assert isinstance(node,TreeMixin),u'非法节点'

        cls=self._model_class

        #如果在同一棵树，则需要判断一下节点之间的关系
        #如果两个节点是一样的，或者ref_node是Node是后代，则移动操作不允许
        if self.get_node_tree_id(ref_node)==self.get_node_tree_id(node):
            R=self.get_node_relation(ref_node,node)
            if R==TREE_NODE_RELATION.Descendants or R==TREE_NODE_RELATION.Self:
                raise TreeNodeInvalidOperation

        node_left=node.tree_left
        node_right=node.tree_right
        node_level=node.tree_level
        node_tree_id=self.get_node_tree_id(node)

        node_count=(node_right-node_left-1)/2+1#所有子孙节点数量，加自己
        node_offset=node_count*2

        #找出所有子孙节点,包括自己
        move_nodes= [item.id for item in self._session.query(cls).filter(and_(cls.tree_left>=node_left,cls.tree_left<=node_right,cls.__dict__[cls.__tree_key__]==node_tree_id)).order_by(cls.tree_left)]

        #先模拟删除该节点,更新相关的节点left,right值
        #执行以下两句后，要移动的节点就从树中脱离，但并没有实际删除
        self._session.query(cls)\
            .filter(and_(cls.tree_left>node_right,cls.__dict__[cls.__tree_key__]==node_tree_id))\
            .update({cls.tree_left:cls.tree_left-(node_right-node_left+1)})
        self._session.query(cls)\
            .filter(and_(cls.tree_right>node_right,cls.__dict__[cls.__tree_key__]==node_tree_id))\
            .update({cls.tree_right:cls.tree_right-(node_right-node_left+1)})

        #模拟删节点后，refnode的left,right值发生变化需要重新取得
        ref_left=ref_node.tree_left
        ref_right=ref_node.tree_right
        ref_level=ref_node.tree_level
        ref_tree_id=self.get_node_tree_id(ref_node)

        if pos==0:#最后一个子节点
            #先移动到最后一个子节点
            self._session.query(cls).filter(cls.id.in_(move_nodes)).update({
                cls.tree_left:cls.tree_left-(node_left-ref_right),
                cls.tree_level:ref_level+(cls.tree_level-node_level)+1,
                cls.tree_right:cls.tree_right-(node_left-ref_right),
                cls.__tree_key__: ref_tree_id                    #更新tree id
            },synchronize_session="fetch")

            #调整个后续节点,只调整同一棵树
            self._session.query(cls).filter(
                and_(~cls.id.in_(move_nodes),cls.tree_left>ref_right,cls.__dict__[cls.__tree_key__]==ref_tree_id))\
                .update({cls.tree_left:cls.tree_left+node_offset},synchronize_session="fetch")
            self._session.query(cls).filter(
                and_(~cls.id.in_(move_nodes),cls.tree_right>=ref_right,cls.__dict__[cls.__tree_key__]==ref_tree_id))\
                .update({cls.tree_right:cls.tree_right+node_offset},synchronize_session="fetch")

        elif pos==1:#第一个子节点
            #先移动到第一个子节点
            self._session.query(cls).filter(cls.id.in_(move_nodes)).update({
                cls.tree_left:cls.tree_left+(ref_left-node_left+1),
                cls.tree_right:cls.tree_right+(ref_left-node_left+1),
                cls.tree_level:ref_level+(cls.tree_level-node_level)+1,
                cls.__tree_key__:ref_tree_id
            },synchronize_session="fetch")

            #调整移动操作导致后续节点RL值变化,以下调整相应的RL值
            self._session.query(cls)\
                .filter(and_(~cls.id.in_(move_nodes),cls.tree_left>ref_left,cls.__dict__[cls.__tree_key__]==ref_tree_id))\
                .update({cls.tree_left:cls.tree_left+node_count*2},synchronize_session="fetch")
            self._session.query(cls)\
                .filter(and_(~cls.id.in_(move_nodes),cls.tree_right>ref_left,cls.__dict__[cls.__tree_key__]==ref_tree_id))\
                .update({cls.tree_right:cls.tree_right+node_count*2},synchronize_session="fetch")

        elif pos==2:#2:移动到下一节点，
            #移动到下一节点
            self._session.query(cls)\
                .filter(cls.id.in_(move_nodes))\
                .update({
                    cls.tree_left:ref_right+(cls.tree_left-node_left)+1,
                    cls.tree_right:cls.tree_right+(ref_left-node_left+1)+1,
                    cls.tree_level:ref_level+(cls.tree_level-node_level),
                    cls.__tree_key__:ref_tree_id
                },synchronize_session="fetch")
            #调整个后续节点
            self._session.query(cls)\
                .filter(and_(~cls.id.in_(move_nodes),cls.tree_left>ref_left,cls.__dict__[cls.__tree_key__]==ref_tree_id))\
                .update({cls.tree_left:cls.tree_left+node_count*2},synchronize_session="fetch")
            self._session.query(cls)\
                .filter(and_(~cls.id.in_(move_nodes),cls.tree_right>ref_right,cls.__dict__[cls.__tree_key__]==ref_tree_id))\
                .update({cls.tree_right:cls.tree_right+node_count*2},synchronize_session="fetch")

        elif pos==3:#3:移到上一节点
            #移动到上一节点
            self._session.query(cls)\
                .filter(cls.id.in_(move_nodes))\
                .update({
                    cls.tree_left:ref_left+(cls.tree_left-node_left),
                    cls.tree_right:cls.tree_right+(ref_left-node_left),
                    cls.tree_level:ref_level+(cls.tree_level-node_level),
                    cls.__tree_key__:ref_tree_id
                },synchronize_session="fetch")
            #调整个后续节点
            self._session.query(cls)\
                .filter(and_(~cls.id.in_(move_nodes),cls.tree_left>=ref_left,cls.__dict__[cls.__tree_key__]==ref_tree_id)).\
                update({cls.tree_left:cls.tree_left+node_count*2},synchronize_session="fetch")
            self._session.query(cls)\
                .filter(and_(~cls.id.in_(move_nodes),cls.tree_right>=ref_right,cls.__dict__[cls.__tree_key__]==ref_tree_id))\
                .update({cls.tree_right:cls.tree_right+node_count*2},synchronize_session="fetch")

    def move_node_up(self,node,allow_upgrade=True):
        """
        将节点上移一步
        :param allow_upgrade: 当移动到最上面时，是否继续上移为父节点的下一个兄弟节点
        :return:
        """
        #取得上一个兄弟节点
        try:
            ref_node=self.get_previous_sibling(node)
            self.move_node(node,ref_node,pos=TREE_NODE_POSITION.PreviousSibling)
        except TreeNodeNotFound:#不存在前一个节点，则需要升级并移动父点的下一个节点
            if allow_upgrade:
                ref_node=self.get_parent(node)
                self.move_node(node,ref_node,pos=TREE_NODE_POSITION.NextSibling)
            else:
                raise TreeNodeInvalidOperation

    def move_node_down(self,node,allow_downgrade=True):
        """
        :param allow_downgrade: 当移动到最下面时，是否继续上移为父节点的下一个兄弟节点
        :return:
        """
        #取得上一个兄弟节点
        try:
            ref_node=self.get_previous_sibling(node)
            self.move_node(node,ref_node,pos=TREE_NODE_POSITION.NextSibling)
        except TreeNodeNotFound:#不存在下一个节点，则需要升级并移动父点的下一个节点
            if allow_downgrade:
                ref_node=self.get_parent(node)
                self.move_node(node,ref_node,pos=TREE_NODE_POSITION.NextSibling)
            else:
                raise TreeNodeInvalidOperation
    def move_node_right(self,node):
        """
        将当前节点调整为上一个节点的子节点
        :param node:
        :return:
        """
        try:
            #取得上一个兄弟节点
            ref_node=self.get_previous_sibling(node)
            self.move_node(node,ref_node,pos=TREE_NODE_POSITION.LastChild)
        except TreeNodeNotFound:#不存在下一个节点，则需要升级并移动父点的下一个节点
            raise TreeNodeInvalidOperation

    def move_node_left(self,node):
        try:
            #取得上一个兄弟节点
            ref_node=self.get_parent(node)
            self.move_node(node,ref_node,pos=TREE_NODE_POSITION.NextSibling)
        except TreeNodeNotFound:#不存在下一个节点，则需要升级并移动父点的下一个节点
            raise TreeNodeInvalidOperation

    def get_trees(self):
        """ 取得存储的树清单
         """
        root_nodes=self.get_nodes(level=1)
        return root_nodes

    def verify_tree(self,tree_id=0):
        """
            通过检查树的左右值来校验树结构的完整性
        当树结构被破坏时，表现在tree_left，tree_right、tree_level值不正确
        如果tree_level不正确，而tree_left,tree_right正确，则tree_level是可以修复的。
        而如果tree_left,tree_right不正确，则整棵树结构就被破坏了。
        :param tree_id:树标识，如果没有指定则校验所有树
        :return:树结构有效返回True
        """
        cls=self._model_class
        rs=self._session.query(cls).filter(cls.__dict__[cls.__tree_key__]==tree_id).order_by(self._get_tree_sort_key(),"tree_left").options(load_only(self.get_primary_field().name,cls.__tree_key__,"tree_left","tree_right","tree_level"))
        nodes=[(item.tree_left,item.tree_right,item.tree_level) for item in rs]
        node_values=[]

        def check_node(cur_node,descendant_nodes):
            if cur_node[1]-cur_node[0]==1:#没有子节点
                node_values.append(cur_node[0])
                node_values.append(cur_node[1])
            elif cur_node[1]-cur_node[0] > 1:#有子节点
                #计算出子节点
                node_values.append(cur_node[0])
                child_nodes=filter(lambda node: node[0]>cur_node[0] and node[1]< cur_node[1] and node[2]==cur_node[2]+1,descendant_nodes)
                for node in child_nodes:
                    check_node(node,filter(lambda item: item[0]>node[0] and item[1]<node[1],descendant_nodes))
                node_values.append(cur_node[1])

        check_node(nodes[0],filter(lambda node: node[0]>1 and node[1]< 2*len(nodes) ,nodes))

        #如果上述检查合法，则应该得到一个[1,2,3,4,.........n]的序列
        #这个序列总数应等一下总记录数的两倍，并且是一个序列
        if len(node_values)!=len(nodes)*2:
            return False
        for v in range(1,len(node_values)):
            if v!=node_values[v-1]:
                return False
        return True

    def get_node_relation(self,node,ref_node):
        """
            取得节点的相对关系
            node:当前节点
            ref_node：相对节点
            Return:0-两个节点相等，1-子节点，2-后代节点，3-父节点，4-祖先节点,5-兄弟节点
            例：
                n=tm.get_node_relation(node1,node2)
                n=1：说明node1是node2的子节点
        """
        tree_id=self.get_node_tree_id(node)
        ref_tree_id=self.get_node_tree_id(ref_node)

        if tree_id==ref_tree_id:#同一棵树的比较
            if node is ref_node:#两个节点相等
                result=TREE_NODE_RELATION.Self
            elif node.tree_left>ref_node.tree_left and node.tree_right<ref_node.tree_right and node.tree_level+1==ref_node.tree_level:
                result= TREE_NODE_RELATION.Child
            elif node.tree_left>ref_node.tree_left and node.tree_right<ref_node.tree_right:
                result=TREE_NODE_RELATION.Descendants #后代
            elif node.tree_left<ref_node.tree_left and node.tree_right>ref_node.tree_right and node.tree_level==ref_node.tree_level+1:
                result=TREE_NODE_RELATION.Parent
            elif node.tree_left<ref_node.tree_left and node.tree_right>ref_node.tree_right:
                result= TREE_NODE_RELATION.Ancestors                 #祖先
            elif node.tree_level==ref_node.tree_level:          #
                #兄弟姐妹节点应具有同一父节点
                #先取得父节点
                parent_node=None
                try:
                    parent_node=self.get_parent(node)
                except:
                    pass
                #如果没有父节点,说明已经是根节点或者出错了
                if parent_node is None:
                    result= TREE_NODE_RELATION.Unknow
                else:
                    #两个节点均同时大于父节点的Left，小于Right
                    if node.tree_left>parent_node.tree_left and node.tree_right<parent_node.tree_right and ref_node.tree_left>parent_node.tree_left and ref_node.tree_right<parent_node.tree_right:
                        result=TREE_NODE_RELATION.Siblings
                    else:#如果不满足，则说明不是兄弟节点，但是同一辈分
                        result=TREE_NODE_RELATION.Same_level
            else:
                result=TREE_NODE_RELATION.Same_tree
        else:       #不同树的比较
            if node.tree_left==ref_node.tree_left==1:  #均是根节点，两个根节点是兄弟关系
                result=TREE_NODE_RELATION.Siblings
            else:                                       #不同树之间
                result=TREE_NODE_RELATION.Diff_tree        #不同树

        return result


    def get_ancestors(self,node):
        """
            取得所有祖先节点,包括父节点
        """
        cls=self._model_class
        return self._session.query(cls)\
            .filter(and_(
                cls.tree_left<node.tree_left,
                cls.tree_right>node.tree_right,
                cls.__dict__[cls.__tree_key__]==self.get_node_tree_id(node)
            )).order_by("tree_left").all()

    def get_parent(self,node):
        """
            取得节点的父节点
        """
        cls=self._model_class
        if node.tree_level==1 and node.tree_left==1: #根节点没有父
            raise TreeNodeNotFound
        else:
            return self._session.query(self._model_class)\
                .filter(and_(
                    cls.tree_left<node.tree_left,
                    cls.tree_right>node.tree_right,
                    cls.__dict__[cls.__tree_key__]==self.get_node_tree_id(node)
                )).order_by("-tree_left").first()

    def get_ancestors_count(self,node):
        """
        取得祖先节点数量,不包括自己
        :param node:
        :return:
        """
        cls=self._model_class
        return self._session.query(func.count(self._model_class))\
                .filter(and_(
                    cls.tree_left<node.tree_left,
                    cls.tree_right>node.tree_right,
                    cls.__dict__[cls.__tree_key__]==self.get_node_tree_id(node)
        )).scalar()

    def get_descendants(self,node,level=0):
        """
        所有后代节点
        :param level:仅返回几级后代,如果=1相当于只返回子节点
        :return:
        """
        cls=self._model_class
        tree_id=self.get_node_tree_id(node)
        if level==0:
            return self._session.query(cls)\
                .filter(and_(
                    cls.tree_left>node.tree_left,
                    cls.tree_right<node.tree_right,
                    cls.__dict__[cls.__tree_key__]==self.get_node_tree_id(node)
                )).order_by("tree_left").all()
        else:
            return self._session.query(cls)\
                .filter(and_(
                    cls.tree_left>node.tree_left,
                    cls.tree_right<node.tree_right,
                    cls.__dict__[cls.__tree_key__]==self.get_node_tree_id(node),
                    cls.tree_level>node.tree_level,
                    cls.tree_level<=node.tree_level+level,
                )).order_by("tree_left").all()

    def get_children(self,node):
        """
         取得所有子节点
         :return:
        """
        return self.get_descendants(node,1)

    def get_descendants_count(self,node):
        """
        取得后代节点数目
        :param node:
        :return:
        """
        return (node.tree_right-node.tree_left-1)/2

    def is_root(self,node):
        """
        返回节点是否是根节点
        :param node:
        :return:
        """
        return node.tree_left==1

    def get_siblings(self,node,include_self=False):
        """
        获取所有兄弟节点
        :param node:
        :param include_self:
        :return:
        """
        cls=self._model_class
        parent_node=self.get_parent(node)
        result_nodes=[]
        if parent_node is None:#根节点
            result_nodes=self._session.query(cls).filter(cls.tree_left==1).order_by(self._get_tree_sort_key()).all()
            try:
                if not include_self:#不包括自己
                    result_nodes.remove(node)
            except:
                pass
        else:
            result_nodes=self.get_children(parent_node)
            if not include_self:
                result_nodes.remove(node)
        return result_nodes

    def get_next_sibling(self,node):
        """取得下一个兄弟节点"""
        cls=self._model_class
        #根节点的下一个兄弟就是下一个根节点
        try:
            if self.is_root(node):
                root_nodes=self._session.query(cls).filter(cls.tree_left==1).order_by(self._get_tree_sort_key()).all()
                next_node= root_nodes[root_nodes.index(node)+1]
            else:
                #先取得下一节点
                #下一节点应满足：同一级别，同一棵树,Left要大于node.tree_left,且具有同一个
                next_node=self._session.query(cls)\
                    .filter(and_(
                        cls.__dict__[cls.__tree_key__]==self.get_node_tree_id(node),
                        cls.tree_left>node.tree_left,
                        cls.tree_level==node.tree_level
                    )).order_by("tree_left").first()
                #满足上述条件的节点，可能只是同一辈分的节点,因此需要再重新排除
                if next_node is not None:
                    parent_node=self.get_parent(next_node)
                    if not (next_node.tree_left>node.tree_left and next_node.tree_right<parent_node.tree_right):
                        next_node=None
            if next_node is None:
                raise TreeNodeNotFound
            return next_node
        except:
            raise TreeNodeNotFound

    def get_previous_sibling(self,node):
        """取得上一个兄弟节点"""
        cls=self._model_class
        #根节点的下一个兄弟就是下一个根节点
        try:
            if self.is_root(node):
                root_nodes=self._session.query(cls).filter(cls.tree_left==1).order_by(self._get_tree_sort_key()).all()
                pre_node= root_nodes[root_nodes.index(node)-1]
            else:
                #先取得下一节点
                #下一节点应满足：同一级别，同一棵树,Left要大于node.tree_left,且具有同一个父节点
                pre_node=self._session.query(cls)\
                    .filter(and_(
                        cls.__dict__[cls.__tree_key__]==self.get_node_tree_id(node),
                        cls.tree_left<node.tree_left,
                        cls.tree_level==node.tree_level
                    )).order_by("-tree_left").first()
                #满足上述条件的节点，可能只是同一辈分的节点
                if pre_node is not None:
                    parent_node=self.get_parent(pre_node)
                    if not (pre_node.tree_left<node.tree_left and pre_node.tree_right<parent_node.tree_right):
                        pre_node=None
            if pre_node is None:
                raise TreeNodeNotFound
            return pre_node
        except:
            raise TreeNodeNotFound

    def _get_output_fields(self,fields):
        """
        返回要输出的字段名称列表
        :return:
        """
        cls=self._model_class

        #id,tree_id,tree_level三个是必备的字段
        pk_field_name=self.get_primary_field().name
        tree_field_name=self.get_tree_key_field_name()
        output_fields=[pk_field_name,tree_field_name,"tree_level"]

        if len(fields)>=0:
            output_fields.extend(fields)
            return list(set(output_fields))

        #定义在TreeMixin类中的__tree_output_fields__列表，则优先使用
        if hasattr(cls,"__tree_output_fields__"):
            output_fields.extend(cls.__tree_output_fields__)
            return list(set(output_fields))

        #如果没有指定__tree_output_fields__，则如果定义了以下字段，则输出
        if hasattr(cls,"__tree_node_name__"):
            output_fields.append(cls.__tree_node_name__)
        if hasattr(cls,"__tree_node_title___"):
            output_fields.append(cls.__tree_title___)
        if hasattr(cls,"__tree_node_description___"):
            output_fields.append(cls.__tree_description___)
        if hasattr(cls,"__tree_node_icon___"):
            output_fields.append(cls.__tree_icon___)
        if hasattr(cls,"__tree_node_status__"):
            output_fields.append(cls.__tree_node_status__)

        return list(set(output_fields))

    def output(self,nodes=None,level=0,flatted=False,fields=[],format="json",children_name="children",pid_field_name="pId",output_err=False):
        """
         输出节点数据到JSON格式
            nodes:输出该节点清单，如果没有指定则输出所有Tree
            format:输出的格式，取值json,list
            level:限定树级别，0-不限制，所有后代均有输出。1-仅仅输出子节点，2-输出子、孙节点，以此类推
            flatted:False-按树形结构输出，True-提供PID，按平面结构输出
            fields=[]:指定输出的字段，如果没有指定，则按默认的节点输出。如果=*，但输出所有字段、如果指定字段名称，则输出指定的字段。
            pid_field:默认=pId，这样刚好默认可以将输出数据直接用到zTree里面
        """
        if nodes is None:
            nodes=self.get_nodes(level==level)

        if not isinstance(nodes,list):
            nodes=[nodes]
        #主键字段名称
        pk_name=self.get_primary_field().name
        #输出的字段名称列表
        fields=self._get_output_fields(fields)
        if flatted:
            fields.append(pid_field_name)
        fields=list(set(fields))#去重

        #输出指定节点下属的所有后代
        def output_node_tree(node):
            outputs={item[0]:item[1] for item in node.__dict__.iteritems() if item[0] in fields}
            #取得所有后代
            descendants=node._TreeManager.get_descendants(node,level)
            if len(descendants)>0:
                parent_nodes=[]#保存父节点
                pre_level=node.tree_level
                parent_pointer=-1
                #开始遍历所有后代
                for i in range(len(descendants)):
                    cur_level=descendants[i].tree_level
                    cur_data={item[0]:item[1] for item in descendants[i].__dict__.iteritems() if item[0] in fields}
                    if cur_level>pre_level:#降级,找出当前节点以及下面的所有节点
                        if i==0:
                            parent_nodes.append(outputs)
                        else:
                            parent_nodes.append(parent_nodes[-1][children_name][-1])
                        if not parent_nodes[-1].has_key(children_name):
                            parent_nodes[parent_pointer][children_name]=[]
                    elif cur_level<pre_level:#升级
                        del parent_nodes[-(pre_level-cur_level):]
                    parent_nodes[-1][children_name].append(cur_data)
                    pre_level=cur_level
            return outputs
        #扁平结构输出
        def output_node_flatted(node):
            outputs=[{item[0]:item[1] for item in node.__dict__.iteritems() if item[0] in fields}]
            try:
                outputs[0][pid_field_name]=self.get_node_primary(self.get_parent(node))
            except:
                outputs[0][pid_field_name]=""
            #取得所有后代数据
            for d_node in node._TreeManager.get_descendants(node,level):
                outputs.append({item[0]:item[1] for item in d_node.__dict__.iteritems() if item[0] in fields})
            #保存父节点pk值
            parent_node_pk=[]
            pre_level=outputs[0]["tree_level"]
            for i in range(1,len(outputs)):
                cur_level=outputs[i]["tree_level"]
                if cur_level>pre_level:#降级,找出当前节点以及下面的所有节点
                    parent_node_pk.append(outputs[i-1][pk_name])
                elif cur_level<pre_level:#升级
                    del parent_node_pk[-(pre_level-cur_level):]
                outputs[i][pid_field_name]=parent_node_pk[-1]
                pre_level=cur_level
            return outputs

        outputs=[]
        for i in range(len(nodes)):
            try:
                if flatted:#输出平面结构，含PID字段
                    outputs.extend(output_node_flatted(nodes[i]))
                else:
                    outputs.append(output_node_tree(nodes[i]))
            except Exception,E:
                if output_err:
                    outputs.append({"error":E,"node":nodes[i]._TreeManager.get_node_primary(nodes[i])})

        if format.lower()=="json":
            return json.dumps(outputs)
        else:
            return outputs



class TreeMixin(object):
    """
        为ORM Model增加树形存储功能
    """

    # 根据此列来区分不同的树
    # 例：__tree_key__="site",则说明将使用site column的值作为tree_id来标识不同的树
    # 如果为None，则由tree_id字段来区分不同的树,tree_id树需要自己指定
    #
    __tree_key__ = "tree_id"
    __tree_sort__= "tree_id"               #用来声明不同树之间如何排序，如="tree_id"，则根据tree_id字段值来进行树排序
    #__tree_output_fields__=["a","b"]       #设置默认输出的字段列表，*-输出所有字段，[...]：仅仅输出指定的字段
    #__tree_primary_key__="id"              用来声明哪个字段是主键,可以省略。如果多个主健时指定
    #__tree_node_name__="name"              #声明节点名称的字段名称
    #__tree_node_title__=""                 #声明节点标题的字段名称，用来显示
    #__tree_node_description__=""           #声明节点说明的字段名称
    #__tree_node_status__=""                #声明节点状态的字段名称  0-关闭，1-打开但数据未加载,2-打开数据已加载
    #__tree_node_icon__=""                  #声明节点图标的字段名称,一般是图标名称,open,close

    tree_id = Column(Integer, default=0)#用来标识节点是哪一棵树的,默认为零,如果指定__tree_key__为其他值时，则以__tree_key__字段什来标识树，该字段就没有用。
    tree_left = Column(Integer, default=0)
    tree_right = Column(Integer, default=0)
    tree_level = Column(Integer, default=0)
    #用来记录TreeManager实例
    __tree_manager=None
    @property
    def _TreeManager(self):
        if self.__tree_manager is None:
            if  hasattr(self.__class__,"TreeManager"):
                self.__class__.TreeManager.init(self.__class__,self.session)
                self.__tree_manager=self.__class__.TreeManager
            else:
                self.__tree_manager=self.__class__.TreeManager=TreeManager(self.__class__,self.session)
        return self.__tree_manager

    @_TreeManager.setter
    def _TreeManager(self,value):
        self.__tree_manager=value

    #以下属性用来映射到节点字段,以便在不同类别的表中均可以采用同样的属性进行访问
    node_name=property(lambda self:self.__dict__[self.__tree_node_name__] if hasattr(self,"__tree_node_name__") else self.__dict__[self._TreeManager.get_primary_field().name])
    node_title=property(lambda self:self.__dict__[self.__tree_title___] if hasattr(self,"__tree_title___") else self.node_name)
    node_description=property(lambda self:self.__dict__[self.__tree_description___] if hasattr(self,"__tree_description___") else "")
    node_icon=property(lambda self:self.__dict__[self.__tree_icon___] if hasattr(self,"__tree_icon___") else "")
    node_status=property(lambda self:self.__dict__[self.__tree_node_status__] if hasattr(self,"__tree_node_status__") else 0 )
    #返回树Key
    tree_key=property(lambda self:self._TreeManager.get_node_tree_id(self))
    #以下是用来获取节点关联属性的方法
    is_root=property(lambda self:self.tree_left==1)
    next_sibling=property(lambda self:self._TreeManager.get_next_sibling(self))
    previous_sibling=property(lambda self:self._TreeManager.get_previous_sibling(self))
    siblings=property(lambda self:self._TreeManager.get_siblings(self))
    children=property(lambda self:self._TreeManager.get_children(self))
    parent=property(lambda self:self._TreeManager.get_parent(self))
    ancestors=property(lambda self:self._TreeManager.get_ancestors(self))
    ancestors_count=property(lambda self:self._TreeManager.get_ancestors_count(self))
    descendants=property(lambda self:self._TreeManager.get_descendants(self))
    descendants_count=property(lambda self:self._TreeManager.get_descendants_count(self))

    #以下实例方法
    def relation_for(self,ref_node):
        """ 返回与ref_node的关系 """
        return self._TreeManager.get_node_relation(self,ref_node)

    def add_child(self,nodes,first=False):
        """
        增加子节点
        :param node:
        :param first: True-增加为第一个子节点,False-增加为最后一个子节点
        :return:
        """
        self._TreeManager.add_node(nodes,self,pos=TREE_NODE_POSITION.FirstChild if first else TREE_NODE_POSITION.LastChild)

    def add_sibling(self,nodes,next=True):
        """
        增加兄弟节点
        :param node:
        :param next: True:增加为下一个兄弟节点，False-增加为上一个兄弟节点
        :return:
        """
        self._TreeManager.add_node(nodes,self,pos=TREE_NODE_POSITION.NextSibling if next else TREE_NODE_POSITION.PreviousSibling)

    def move_to(self,ref_node,pos=TREE_NODE_POSITION.LastChild):
        """
        移动节点至node的相对位置
        :param node:
        :param pos:
        :return:
        """
        self._TreeManager.move_node(self,ref_node,pos)

    def delete(self):
        """
        删除自身，但不能删当前实例，只是从数据库中删除
        :return:
        """
        self._TreeManager.del_node(self)

    def to_json(self,*args,**kwargs):
        """
        自身并包括后代为json
        :param:参见TreeManager的output方法
        :return:
        """
        return self._TreeManager.output(self,format="json",*args,**kwargs)
    def to_list(self,*args,**kwargs):
        return self._TreeManager.output(self,format="list",*args,**kwargs)
    def move_up(self,allow_upgrade=False):
        self._TreeManager.move_node_up(self,allow_upgrade)
    def move_down(self,allow_downgrade=False):
        self._TreeManager.move_node_down(self,allow_downgrade)
    def move_right(self):
        self._TreeManager.move_node_right(self)
    def move_left(self):
        self._TreeManager.move_node_left(self)