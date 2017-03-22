package readers;

import java.util.List;

import model.tree.Tree;

public interface TreeReader {
	public Tree convertTree(String treeData);
	public List<Tree> convertTrees(String gameData, int lineNumber);
}
